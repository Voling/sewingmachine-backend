from types import SimpleNamespace

import pytest

import src.jobs.athena_runner as runner


class FakeAthena:
    def __init__(self, states):
        self.states = list(states)
        self.started = []
        self.execution_checks = []

    def start_query_execution(self, **kwargs):
        self.started.append(kwargs)
        return {"QueryExecutionId": "qid-123"}

    def get_query_execution(self, **kwargs):
        state = self.states.pop(0)
        self.execution_checks.append(state)
        return {"QueryExecution": {"Status": {"State": state}}}


class FakeEvents:
    def __init__(self):
        self.remove_calls = []
        self.delete_calls = []

    def remove_targets(self, **kwargs):
        self.remove_calls.append(kwargs)

    def delete_rule(self, **kwargs):
        self.delete_calls.append(kwargs)


@pytest.fixture(autouse=True)
def patch_sleep(monkeypatch):
    monkeypatch.setattr(runner, "time", SimpleNamespace(sleep=lambda *_: None))


@pytest.fixture
def base_config():
    return runner.AthenaRunnerConfig(
        output_location="s3://bucket/output/",
        workgroup="primary",
        catalog="AwsDataCatalog",
        event_bus="bus",
    )


def test_run_sql_waits_until_success(monkeypatch, base_config):
    fake_athena = FakeAthena(states=["RUNNING", "SUCCEEDED"])
    service = runner.AthenaRunnerService(fake_athena, FakeEvents(), base_config)

    qid = service._run_sql("SELECT 1", "db")

    assert qid == "qid-123"
    assert fake_athena.started[0]["QueryString"] == "SELECT 1"
    assert fake_athena.started[0]["QueryExecutionContext"]["Database"] == "db"


def test_run_sql_raises_on_failure(monkeypatch, base_config):
    fake_athena = FakeAthena(states=["FAILED"])
    service = runner.AthenaRunnerService(fake_athena, FakeEvents(), base_config)

    with pytest.raises(RuntimeError):
        service._run_sql("SELECT 1", "db")


def test_handler_runs_queries_and_cleans_up(monkeypatch, base_config):
    calls = []

    class StubService(runner.AthenaRunnerService):
        def _run_sql(self, sql: str, database: str) -> str:
            calls.append((sql.strip().splitlines()[0], database))
            return "qid"

    fake_events = FakeEvents()

    monkeypatch.setattr(runner, "_load_config", lambda: base_config)
    monkeypatch.setattr(runner, "AthenaRunnerService", lambda athena_client, events_client, config: StubService(FakeAthena(["SUCCEEDED"]), fake_events, config))

    event = {"run": "2024-01-01", "cleanupRule": "rule-1"}
    response = runner.lambda_handler(event, None)

    assert len(calls) == 8
    assert calls[0][1] == "staging"
    assert calls[-1][1] == "gold"

    assert response["ok"] is True
    assert response["run"] == "2024-01-01"
    assert fake_events.remove_calls[0]["Rule"] == "rule-1"
    assert fake_events.delete_calls[0]["Name"] == "rule-1"
