from types import SimpleNamespace

import pytest

import src.jobs.athena_runner as athena_runner


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


@pytest.fixture(autouse=True)
def patch_sleep(monkeypatch):
    monkeypatch.setattr(athena_runner, "time", SimpleNamespace(sleep=lambda *_: None))


def test_run_sql_waits_until_success(monkeypatch):
    fake_athena = FakeAthena(states=["RUNNING", "SUCCEEDED"])
    monkeypatch.setattr(athena_runner, "athena", fake_athena)

    qid = athena_runner.run_sql("SELECT 1", "db")

    assert qid == "qid-123"
    assert fake_athena.started[0]["QueryString"] == "SELECT 1"
    assert fake_athena.started[0]["QueryExecutionContext"]["Database"] == "db"


def test_run_sql_raises_on_failure(monkeypatch):
    fake_athena = FakeAthena(states=["FAILED"])
    monkeypatch.setattr(athena_runner, "athena", fake_athena)

    with pytest.raises(RuntimeError):
        athena_runner.run_sql("SELECT 1", "db")


def test_handler_runs_queries_and_cleans_up(monkeypatch):
    calls = []

    def fake_run_sql(sql, db):
        calls.append((sql.strip().splitlines()[0], db))
        return "qid"

    monkeypatch.setattr(athena_runner, "run_sql", fake_run_sql)

    events_calls = {}

    class FakeEvents:
        def remove_targets(self, **kwargs):
            events_calls.setdefault("remove", []).append(kwargs)

        def delete_rule(self, **kwargs):
            events_calls.setdefault("delete", []).append(kwargs)

    monkeypatch.setattr(athena_runner, "events", FakeEvents())

    event = {"run": "2024-01-01", "cleanupRule": "rule-1"}
    response = athena_runner.handler(event, None)

    assert len(calls) == 8
    assert calls[0][1] == "staging"
    assert calls[-1][1] == "gold"

    assert response["ok"] is True
    assert response["run"] == "2024-01-01"
    assert events_calls["remove"][0]["Rule"] == "rule-1"
    assert events_calls["delete"][0]["Name"] == "rule-1"
