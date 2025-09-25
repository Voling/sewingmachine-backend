from __future__ import annotations

from typing import Dict, List

from ..config.settings import SchemasSettings
from ..domain.models import DatabaseSummary
from ..infrastructure.aws_clients import AwsClients
from ..presentation.logging import get_logger


_LOGGER = get_logger("sewingmachine.schemas")


class SchemasService:
    def __init__(self, settings: SchemasSettings, clients: AwsClients) -> None:
        self._settings = settings
        self._glue = clients.glue()

    def execute(self) -> Dict[str, List[Dict[str, object]]]:
        databases: List[DatabaseSummary] = []
        paginator = self._glue.get_paginator("get_databases")
        for page in paginator.paginate():
            for db in page.get("DatabaseList", []) or []:
                name = db["Name"]
                tables = self._collect_tables(name)
                databases.append(DatabaseSummary(name=name, tables=tables))
        return {"databases": [db.to_dict() for db in databases]}

    def _collect_tables(self, database: str) -> List[str]:
        tables: List[str] = []
        paginator = self._glue.get_paginator("get_tables")
        for page in paginator.paginate(DatabaseName=database, PaginationConfig={"MaxItems": 200}):
            for table in page.get("TableList", []) or []:
                tables.append(table["Name"])
        return tables
