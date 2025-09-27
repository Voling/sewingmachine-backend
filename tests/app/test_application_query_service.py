import pytest
from botocore.exceptions import ClientError

from app.application.query_service import QueryService
from app.config.settings import QuerySettings
from app.domain.errors import ExternalServiceError, ValidationError


class FakeAthena:
    def __init__(self, *, start_error=None, execution_payloads=None, results_payloads=None):
        self.start_error = start_error
        self.execution_payloads = list(execution_payloads or [])
        self.results_payloads = list(results_payloads or [])
        self.started = []
        self.results_calls = []

    def start_query_execution(self, **kwargs):
        if self.start_error:
            raise self.start_error
        self.started.append(kwargs)
        return {"QueryExecutionId": "qid-123"}

    def get_query_execution(self, **_kwargs):
        if not self.execution_payloads:
            raise AssertionError("No execution payloads left")
        return self.execution_payloads.pop(0)

    def get_query_results(self, **kwargs):
        self.results_calls.append(kwargs)
        if not self.results_payloads:
            raise AssertionError("No results payloads left")
        return self.results_payloads.pop(0)


class FakeClients:
    def __init__(self, athena):
        self._athena = athena

    def athena(self):
        return self._athena


SETTINGS = QuerySettings(
    region="us-west-1",
    allowed_origin="*",
    athena_workgroup="wg",
    athena_output="s3://output/",
    athena_catalog="AwsDataCatalog",
    default_database="analytics",
)


def test_query_execute_new_query_success(monkeypatch):
    execution_payloads = [
        {"QueryExecution": {"Status": {"State": "RUNNING"}}},
        {
            "QueryExecution": {
                "Status": {"State": "SUCCEEDED"},
                "Statistics": {
                    "DataScannedInBytes": 123,
                    "EngineExecutionTimeInMillis": 45,
                },
            }
        },
    ]
    results_payloads = [
        {
            "ResultSet": {
                "ResultSetMetadata": {"ColumnInfo": [{"Label": "col1"}]},
                "Rows": [
                    {"Data": [{"VarCharValue": "col1"}]},
                    {"Data": [{"VarCharValue": "value"}]},
                ],
            }
        }
    ]
    athena = FakeAthena(execution_payloads=execution_payloads, results_payloads=results_payloads)

    monkeypatch.setattr("app.application.query_service.time.sleep", lambda *_: None)

    service = QueryService(SETTINGS, FakeClients(athena))
    result = service.execute({"sql": "SELECT 1", "database": "analytics", "maxRows": 10})

    assert result["columns"] == ["col1"]
    assert result["rows"] == [["value"]]
    assert result["stats"]["scanned_bytes"] == 123
    assert athena.started[0]["QueryExecutionContext"]["Catalog"] == "AwsDataCatalog"


def test_query_execute_existing_query_skips_start():
    results_payloads = [
        {
            "ResultSet": {
                "ResultSetMetadata": {"ColumnInfo": [{"Name": "col1"}]},
                "Rows": [
                    {"Data": [{"VarCharValue": "value"}]},
                ],
            },
            "NextToken": "next-token",
        }
    ]
    athena = FakeAthena(results_payloads=results_payloads)
    service = QueryService(SETTINGS, FakeClients(athena))

    result = service.execute({
        "queryExecutionId": "qid-123",
        "nextPageToken": "tok",
        "maxRows": 2,
    })

    assert result["columns"] == ["col1"]
    assert result["rows"] == [["value"]]
    assert result["next_page_token"] == "next-token"
    assert athena.started == []
    assert athena.results_calls[0]["NextToken"] == "tok"


def test_query_execute_validates_inputs():
    service = QueryService(SETTINGS, FakeClients(FakeAthena()))

    with pytest.raises(ValidationError):
        service.execute({"sql": "SELECT 1", "maxRows": "abc"})

    with pytest.raises(ValidationError):
        service.execute({"maxRows": 10})


def test_query_execute_handles_start_error():
    error = ClientError({"Error": {"Code": "Throttled", "Message": "nope"}}, "StartQueryExecution")
    service = QueryService(SETTINGS, FakeClients(FakeAthena(start_error=error)))

    with pytest.raises(ExternalServiceError):
        service.execute({"sql": "SELECT 1"})


def test_query_execute_handles_failed_state(monkeypatch):
    execution_payloads = [
        {"QueryExecution": {"Status": {"State": "FAILED", "StateChangeReason": "boom"}}}
    ]
    athena = FakeAthena(execution_payloads=execution_payloads, results_payloads=[])
    monkeypatch.setattr("app.application.query_service.time.sleep", lambda *_: None)
    service = QueryService(SETTINGS, FakeClients(athena))

    with pytest.raises(ExternalServiceError):
        service.execute({"sql": "SELECT 1"})
