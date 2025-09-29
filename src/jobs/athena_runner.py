from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Iterable

import boto3
from botocore.config import Config

CLIENT_CONFIG = Config(connect_timeout=3, read_timeout=10)

athena = boto3.client('athena', config=CLIENT_CONFIG)
events = boto3.client('events', config=CLIENT_CONFIG)


@dataclass(frozen=True)
class AthenaRunnerConfig:
    output_location: str
    workgroup: str
    catalog: str
    event_bus: str


@dataclass(frozen=True)
class RefreshRequest:
    run: str
    cleanup_rule: str | None = None


class AthenaRunnerService:
    def __init__(self, athena_client, events_client, config: AthenaRunnerConfig) -> None:
        self._athena = athena_client
        self._events = events_client
        self._config = config

    def run_refresh(self, request: RefreshRequest) -> dict[str, str | bool]:
        self._run_sql(RESIDENT_CTAS.replace(':RUN', request.run), 'staging')
        self._run_sql(VISIT_CTAS.replace(':RUN', request.run), 'staging')

        for statement, database in _MERGE_PIPELINE:
            self._run_sql(statement, database)

        if request.cleanup_rule:
            self._events.remove_targets(
                Rule=request.cleanup_rule,
                Ids=['athena-runner'],
                EventBusName=self._config.event_bus,
            )
            self._events.delete_rule(
                Name=request.cleanup_rule,
                EventBusName=self._config.event_bus,
                Force=True,
            )

        return {"ok": True, "run": request.run}

    def _run_sql(self, sql: str, database: str) -> str:
        response = self._athena.start_query_execution(
            QueryString=sql,
            QueryExecutionContext={"Database": database, "Catalog": self._config.catalog},
            ResultConfiguration={"OutputLocation": self._config.output_location},
            WorkGroup=self._config.workgroup,
        )
        execution_id = response['QueryExecutionId']
        while True:
            status = self._athena.get_query_execution(QueryExecutionId=execution_id)['QueryExecution']['Status']['State']
            if status in {'SUCCEEDED', 'FAILED', 'CANCELLED'}:
                if status != 'SUCCEEDED':
                    raise RuntimeError(f"Athena failed: {status}")
                return execution_id
            time.sleep(2)


def _load_config() -> AthenaRunnerConfig:
    return AthenaRunnerConfig(
        output_location=os.environ['ATHENA_OUTPUT'],
        workgroup=os.environ.get('ATHENA_WG', 'primary'),
        catalog=os.environ.get('ATHENA_CATALOG', 'AwsDataCatalog'),
        event_bus=os.environ.get('EVENTBUS_NAME', 'default'),
    )


def lambda_handler(event, ctx):
    payload = event if isinstance(event, dict) else json.loads(event)
    request = RefreshRequest(
        run=payload.get('run', '2025-08-13'),
        cleanup_rule=payload.get('cleanupRule'),
    )
    service = AthenaRunnerService(athena, events, _load_config())
    result = service.run_refresh(request)
    return result


# SQL strings identical to the top-level version
RESIDENT_CTAS = """
DROP TABLE IF EXISTS staging.dbo_resident_latest;
CREATE TABLE staging.dbo_resident_latest
WITH (
  table_type='ICEBERG',
  format='PARQUET',
  location='s3://fabric-aws-poc/staging/sqlserver/resident_latest/'
) AS
SELECT
  CAST(resident_id AS INT)               AS resident_id,
  TRIM(CAST(first_name AS VARCHAR))      AS first_name,
  TRIM(CAST(last_name  AS VARCHAR))      AS last_name,
  CAST(dob AS DATE)                      AS dob,
  CAST(updated_at AS TIMESTAMP)          AS updated_at,
  CAST(':RUN' AS TIMESTAMP)              AS dms_received_ts
FROM bronze.dbo_resident
WHERE run = DATE ':RUN';
"""

VISIT_CTAS = """
DROP TABLE IF EXISTS staging.dbo_visit_latest;
CREATE TABLE staging.dbo_visit_latest
WITH (
  table_type='ICEBERG',
  format='PARQUET',
  location='s3://fabric-aws-poc/staging/sqlserver/visit_latest/'
) AS
SELECT
  CAST(visit_id AS INT)                  AS visit_id,
  CAST(resident_id AS INT)               AS resident_id,
  CAST(visit_ts AS TIMESTAMP)            AS visit_ts,
  TRIM(CAST(reason AS VARCHAR))          AS reason,
  CAST(charge_cents AS INT)              AS charge_cents,
  CAST(updated_at AS TIMESTAMP)          AS updated_at,
  CAST(':RUN' AS TIMESTAMP)              AS dms_received_ts
FROM bronze.dbo_visit
WHERE run = DATE ':RUN';
"""

RESIDENT_MERGE = """
MERGE INTO silver.src_sqlserver__dbo_resident t
USING staging.dbo_resident_latest s
ON (t.resident_id = s.resident_id)
WHEN MATCHED AND s.updated_at > t.updated_at THEN UPDATE SET
  first_name      = s.first_name,
  last_name       = s.last_name,
  dob             = s.dob,
  updated_at      = s.updated_at,
  dms_received_ts = s.dms_received_ts,
  is_deleted      = FALSE
WHEN NOT MATCHED THEN INSERT (
  resident_id, first_name, last_name, dob, updated_at, dms_received_ts, is_deleted
) VALUES (
  s.resident_id, s.first_name, s.last_name, s.dob, s.updated_at, s.dms_received_ts, FALSE
);
"""

VISIT_MERGE = """
MERGE INTO silver.src_sqlserver__dbo_visit t
USING staging.dbo_visit_latest s
ON (t.visit_id = s.visit_id)
WHEN MATCHED AND s.updated_at > t.updated_at THEN UPDATE SET
  resident_id     = s.resident_id,
  visit_ts        = s.visit_ts,
  reason          = s.reason,
  charge_cents    = s.charge_cents,
  updated_at      = s.updated_at,
  dms_received_ts = s.dms_received_ts,
  is_deleted      = FALSE
WHEN NOT MATCHED THEN INSERT (
  visit_id, resident_id, visit_ts, reason, charge_cents, updated_at, dms_received_ts, is_deleted
) VALUES (
  s.visit_id, s.resident_id, s.visit_ts, s.reason, s.charge_cents, s.updated_at, s.dms_received_ts, FALSE
);
"""

RESIDENT_SOFT_DELETE = """
UPDATE silver.src_sqlserver__dbo_resident t
SET is_deleted = TRUE
WHERE is_deleted IS DISTINCT FROM TRUE
  AND NOT EXISTS (SELECT 1 FROM staging.dbo_resident_latest s WHERE s.resident_id = t.resident_id);
"""

VISIT_SOFT_DELETE = """
UPDATE silver.src_sqlserver__dbo_visit t
SET is_deleted = TRUE
WHERE is_deleted IS DISTINCT FROM TRUE
  AND NOT EXISTS (SELECT 1 FROM staging.dbo_visit_latest s WHERE s.visit_id = t.visit_id);
"""

DIM_RESIDENT_MERGE = """
MERGE INTO gold.dim_resident d
USING (
  SELECT
    resident_id,
    first_name,
    last_name,
    CONCAT(first_name,' ',last_name) AS full_name,
    dob,
    CAST(date_diff('year', dob, current_date) AS INT) AS age_years,
    MAX(dms_received_ts) AS effective_ts
  FROM silver.src_sqlserver__dbo_resident
  WHERE is_deleted IS DISTINCT FROM TRUE
  GROUP BY resident_id, first_name, last_name, dob
) s
ON (d.resident_id = s.resident_id)
WHEN MATCHED THEN UPDATE SET
  first_name   = s.first_name,
  last_name    = s.last_name,
  full_name    = s.full_name,
  dob          = s.dob,
  age_years    = s.age_years,
  effective_ts = s.effective_ts
WHEN NOT MATCHED THEN INSERT (
  resident_id, first_name, last_name, full_name, dob, age_years, effective_ts
) VALUES (
  s.resident_id, s.first_name, s.last_name, s.full_name, s.dob, s.age_years, s.effective_ts
);
"""

FACT_VISIT_MERGE = """
MERGE INTO gold.fact_visit f
USING (
  SELECT
    v.visit_id,
    v.resident_id,
    CAST(date_trunc('day', v.visit_ts) AS DATE) AS visit_date,
    v.visit_ts,
    v.reason,
    v.charge_cents,
    CAST(v.charge_cents / 100.0 AS DECIMAL(12,2)) AS charge_usd
  FROM silver.src_sqlserver__dbo_visit v
  JOIN silver.src_sqlserver__dbo_resident r
    ON r.resident_id = v.resident_id
  WHERE (v.is_deleted IS DISTINCT FROM TRUE) AND (r.is_deleted IS DISTINCT FROM TRUE)
) s
ON (f.visit_id = s.visit_id)
WHEN MATCHED THEN UPDATE SET
  resident_id = s.resident_id,
  visit_date  = s.visit_date,
  visit_ts    = s.visit_ts,
  reason      = s.reason,
  charge_cents= s.charge_cents,
  charge_usd  = s.charge_usd
WHEN NOT MATCHED THEN INSERT (
  visit_id, resident_id, visit_date, visit_ts, reason, charge_cents, charge_usd
) VALUES (
  s.visit_id, s.resident_id, s.visit_date, s.visit_ts, s.reason, s.charge_cents, s.charge_usd
);
"""

_MERGE_PIPELINE: Iterable[tuple[str, str]] = (
    (RESIDENT_MERGE, 'silver'),
    (VISIT_MERGE, 'silver'),
    (RESIDENT_SOFT_DELETE, 'silver'),
    (VISIT_SOFT_DELETE, 'silver'),
    (DIM_RESIDENT_MERGE, 'gold'),
    (FACT_VISIT_MERGE, 'gold'),
)
