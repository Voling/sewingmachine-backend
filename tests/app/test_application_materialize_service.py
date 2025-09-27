from types import SimpleNamespace

import pytest
from botocore.exceptions import ClientError

from app.application.materialize_service import MaterializeService
from app.config.settings import MaterializeSettings
from app.domain.errors import ExternalServiceError, ValidationError


class FakeAthena:
    def __init__(self, states=None, start_error=None):
        self.states = states or ["SUCCEEDED"]
        self.start_error = start_error
        self.started = []
        self._calls = 0

    def start_query_execution(self, **kwargs):
        if self.start_error:
            raise self.start_error
        self.started.append(kwargs)
        return {"QueryExecutionId": "qid-123"}

    def get_query_execution(self, **_kwargs):
        state = self.states[min(self._calls, len(self.states) - 1)]
        self._calls += 1
        payload = {"QueryExecution": {"Status": {"State": state}}}
        if state != "SUCCEEDED":
            payload["QueryExecution"]["Status"]["StateChangeReason"] = "bad state"
        return payload


class FakeClients:
    def __init__(self, athena):
        self._athena = athena

    def athena(self):
        return self._athena


SETTINGS = MaterializeSettings(
    region="us-west-1",
    allowed_origin="*",
    athena_workgroup="wg",
    athena_output="s3://output/",
)


@pytest.fixture(autouse=True)
def patch_sleep(monkeypatch):
    monkeypatch.setattr("app.application.materialize_service.time", SimpleNamespace(sleep=lambda *_: None))


def test_materialize_execute_append(monkeypatch):
    athena = FakeAthena(states=["RUNNING", "SUCCEEDED"])
    service = MaterializeService(SETTINGS, FakeClients(athena))

    result = service.execute({
        "mode": "append",
        "target": {"db": "analytics", "table": "visits"},
        "sql": "SELECT * FROM source",
    })

    assert result["status"] == "ok"
    assert "INSERT INTO analytics.visits" in athena.started[0]["QueryString"]
    assert athena.started[0]["WorkGroup"] == "wg"


def test_materialize_execute_replace_with_props(monkeypatch):
    athena = FakeAthena(states=["SUCCEEDED"])
    service = MaterializeService(SETTINGS, FakeClients(athena))

    service.execute({
        "mode": "replace",
        "target": {"db": "analytics", "table": "visits"},
        "sql": "SELECT 1",
        "properties": {"format": "PARQUET", "compression": "SNAPPY"},
    })

    query = athena.started[0]["QueryString"]
    assert "'compression' = 'SNAPPY'" in query
    assert query.startswith("DROP TABLE IF EXISTS")


def test_materialize_execute_validates_sql():
    service = MaterializeService(SETTINGS, FakeClients(FakeAthena()))

    with pytest.raises(ValidationError):
        service.execute({
            "target": {"db": "analytics", "table": "visits"},
            "sql": "DELETE FROM table",
        })


def test_materialize_execute_handles_athena_failure():
    athena = FakeAthena(states=["FAILED"])
    service = MaterializeService(SETTINGS, FakeClients(athena))

    with pytest.raises(ExternalServiceError):
        service.execute({
            "target": {"db": "analytics", "table": "visits"},
            "sql": "SELECT 1",
        })


def test_materialize_execute_handles_start_error():
    error = ClientError({"Error": {"Code": "ThrottlingException", "Message": "throttled"}}, "StartQueryExecution")
    athena = FakeAthena(states=[], start_error=error)
    service = MaterializeService(SETTINGS, FakeClients(athena))

    with pytest.raises(ExternalServiceError):
        service.execute({
            "target": {"db": "analytics", "table": "visits"},
            "sql": "SELECT 1",
        })
