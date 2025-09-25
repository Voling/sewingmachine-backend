from __future__ import annotations

import time
from typing import Dict, List, Optional

from botocore.exceptions import ClientError

from ..config.settings import QuerySettings
from ..domain.errors import ExternalServiceError, ValidationError
from ..domain.models import QueryResultPage, QueryStatistics
from ..infrastructure.aws_clients import AwsClients
from ..presentation.logging import get_logger


_LOGGER = get_logger("sewingmachine.query")


class QueryService:
    def __init__(self, settings: QuerySettings, clients: AwsClients) -> None:
        self._settings = settings
        self._athena = clients.athena()

    def execute(self, payload: Dict[str, object]) -> Dict[str, object]:
        sql = payload.get("sql")
        query_execution_id = payload.get("queryExecutionId")
        next_token = payload.get("nextPageToken")
        max_rows = self._sanitize_max_rows(payload.get("maxRows"))
        database = self._select_database(payload)

        if not (sql or query_execution_id):
            raise ValidationError("sql or queryExecutionId required", code="MissingParam")

        stats = QueryStatistics(scanned_bytes=None, execution_time_ms=None)
        query_id = str(query_execution_id) if query_execution_id else None

        if not next_token and query_id is None:
            query_id, execution = self._start_query(str(sql), database)
            status = execution.get("Status", {})
            statistics = execution.get("Statistics", {})
            stats = QueryStatistics(
                scanned_bytes=statistics.get("DataScannedInBytes"),
                execution_time_ms=statistics.get("EngineExecutionTimeInMillis"),
            )
            if status.get("State") != "SUCCEEDED":
                reason = status.get("StateChangeReason", "")
                raise ExternalServiceError(f"Athena {status.get('State')}: {reason}")

        read_query_id = query_id or str(query_execution_id)
        if not read_query_id:
            raise ValidationError("queryExecutionId missing", code="MissingParam")

        columns, rows, next_page_token = self._read_page(read_query_id, next_token, max_rows)
        result_page = QueryResultPage(
            columns=columns,
            rows=rows,
            stats=stats,
            query_execution_id=read_query_id,
            next_page_token=next_page_token,
        )
        return result_page.to_dict()

    def _sanitize_max_rows(self, value: object) -> int:
        try:
            max_rows = int(value or 500)
        except (TypeError, ValueError):
            raise ValidationError("maxRows must be an integer", code="BadParam")
        return max(1, min(max_rows, 1000))

    def _select_database(self, payload: Dict[str, object]) -> Optional[str]:
        database = (payload.get("catalog") or payload.get("database") or "").strip()
        if database:
            return database
        return self._settings.default_database

    def _start_query(self, sql: str, database: Optional[str]):
        context = {"Catalog": self._settings.athena_catalog}
        if database:
            context["Database"] = database
        try:
            response = self._athena.start_query_execution(
                QueryString=sql,
                QueryExecutionContext=context,
                ResultConfiguration={"OutputLocation": self._settings.athena_output},
                WorkGroup=self._settings.athena_workgroup,
            )
        except ClientError as exc:
            _LOGGER.error("Failed to start Athena query", exc_info=True)
            raise ExternalServiceError("Failed to start Athena query") from exc

        query_id = response["QueryExecutionId"]
        while True:
            execution = self._athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]
            state = execution["Status"]["State"]
            if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
                return query_id, execution
            time.sleep(0.4)

    def _read_page(self, query_id: str, token: Optional[str], max_rows: int):
        kwargs = {"QueryExecutionId": query_id, "MaxResults": max_rows}
        if token:
            kwargs["NextToken"] = token
        out = self._athena.get_query_results(**kwargs)
        columns = [col.get("Label") or col.get("Name") for col in out["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]]
        rows: List[List[Optional[str]]] = []
        result_rows = out["ResultSet"].get("Rows", [])
        start_idx = 1 if not token and result_rows else 0
        for row in result_rows[start_idx:]:
            rows.append([cell.get("VarCharValue") if "VarCharValue" in cell else None for cell in row.get("Data", [])])
        return columns, rows, out.get("NextToken")
