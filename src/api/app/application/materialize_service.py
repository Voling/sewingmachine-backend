from __future__ import annotations

import time
from typing import Dict

from botocore.exceptions import ClientError

from ..config.settings import MaterializeSettings
from ..domain.errors import DomainError, ValidationError, ExternalServiceError
from ..infrastructure.aws_clients import AwsClients
from ..presentation.logging import get_logger


_LOGGER = get_logger("sewingmachine.materialize")


class MaterializeService:
    def __init__(self, settings: MaterializeSettings, clients: AwsClients) -> None:
        self._settings = settings
        self._athena = clients.athena()

    def execute(self, payload: Dict[str, object]) -> Dict[str, object]:
        mode = str(payload.get("mode") or "append").lower()
        target = payload.get("target") or {}
        sql = payload.get("sql")
        properties = payload.get("properties") or {}

        if not isinstance(target, dict):
            raise ValidationError("target must be an object")

        database = target.get("db")
        table = target.get("table")

        if not database or not table or not sql:
            raise ValidationError("target.db, target.table and sql are required", code="MissingParam")
        if mode not in {"append", "replace"}:
            raise ValidationError("mode must be append or replace", code="BadParam")
        if not self._is_select_statement(str(sql)):
            raise ValidationError("sql must be a SELECT statement", code="UnsafeSql")

        athena_sql = self._compose_sql(mode, str(sql), str(database), str(table), properties)
        query_id = self._start_and_wait(athena_sql, str(database))

        return {
            "status": "ok",
            "table": f"{database}.{table}",
            "mode": mode,
            "qid": query_id,
        }

    def _compose_sql(self, mode: str, select_sql: str, database: str, table: str, props: Dict[str, object]) -> str:
        if mode == "replace":
            if props:
                props_sql = ", ".join(f"'{k}' = '{v}'" for k, v in props.items())
            else:
                props_sql = "table_type = 'ICEBERG', format = 'PARQUET'"
            return f"DROP TABLE IF EXISTS {database}.{table};\nCREATE TABLE {database}.{table} WITH ({props_sql}) AS {select_sql}"
        return f"INSERT INTO {database}.{table} {select_sql}"

    def _start_and_wait(self, sql: str, database: str) -> str:
        try:
            response = self._athena.start_query_execution(
                QueryString=sql,
                QueryExecutionContext={"Database": database},
                ResultConfiguration={"OutputLocation": self._settings.athena_output},
                WorkGroup=self._settings.athena_workgroup,
            )
        except ClientError as exc:
            _LOGGER.error("Failed to start Athena query", exc_info=True)
            raise ExternalServiceError("Failed to start Athena query") from exc

        query_id = response["QueryExecutionId"]
        while True:
            execution = self._athena.get_query_execution(QueryExecutionId=query_id)
            state = execution["QueryExecution"]["Status"]["State"]
            if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
                if state != "SUCCEEDED":
                    reason = execution["QueryExecution"]["Status"].get("StateChangeReason", "")
                    raise ExternalServiceError(f"Athena {state}: {reason}")
                return query_id
            time.sleep(0.5)

    def _is_select_statement(self, sql: str) -> bool:
        statement = sql.strip().lower()
        if not statement.startswith("select"):
            return False
        banned = [";create ", ";drop ", ";alter ", " insert ", " merge ", " delete ", " update "]
        return not any(token in statement for token in banned)
