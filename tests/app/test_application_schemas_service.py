from app.application.schemas_service import SchemasService
from app.config.settings import SchemasSettings


class FakeGlueDatabasesPaginator:
    def __init__(self, pages):
        self._pages = pages

    def paginate(self):
        for page in self._pages:
            yield page


class FakeGlueTablesPaginator:
    def __init__(self, table_pages):
        self._table_pages = table_pages
        self.calls = []

    def paginate(self, *, DatabaseName, PaginationConfig):
        self.calls.append((DatabaseName, PaginationConfig))
        for page in self._table_pages.get(DatabaseName, []):
            yield page


class FakeGlue:
    def __init__(self, db_pages, table_pages):
        self.databases_paginator = FakeGlueDatabasesPaginator(db_pages)
        self.tables_paginator = FakeGlueTablesPaginator(table_pages)

    def get_paginator(self, name):
        if name == "get_databases":
            return self.databases_paginator
        if name == "get_tables":
            return self.tables_paginator
        raise NotImplementedError(name)


class FakeClients:
    def __init__(self, glue):
        self._glue = glue

    def glue(self):
        return self._glue


SETTINGS = SchemasSettings(region="us-west-1", allowed_origin="*")


def test_schemas_service_collects_tables():
    db_pages = [
        {"DatabaseList": [{"Name": "db1"}]},
        {"DatabaseList": [{"Name": "db2"}]},
    ]
    table_pages = {
        "db1": [{"TableList": [{"Name": "t1"}, {"Name": "t2"}]}],
        "db2": [{"TableList": []}],
    }
    glue = FakeGlue(db_pages, table_pages)

    service = SchemasService(SETTINGS, FakeClients(glue))
    result = service.execute()

    assert result["databases"][0] == {"name": "db1", "tables": ["t1", "t2"]}
    assert result["databases"][1] == {"name": "db2", "tables": []}
    assert glue.tables_paginator.calls[0][0] == "db1"
