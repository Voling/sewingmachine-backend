import json

import pytest

import src.jobs.orchestrator as orchestrator


class FakeDMS:
    def __init__(self):
        self.calls = []

    def start_replication_task(self, **kwargs):
        self.calls.append(kwargs)


class FakeEvents:
    def __init__(self):
        self.put_rule_calls = []
        self.put_targets_calls = []

    def put_rule(self, **kwargs):
        self.put_rule_calls.append(kwargs)
        return {"RuleArn": "arn:rule"}

    def put_targets(self, **kwargs):
        self.put_targets_calls.append(kwargs)


class FakeLambda:
    def __init__(self):
        self.permissions = []

    def add_permission(self, **kwargs):
        self.permissions.append(kwargs)


@pytest.fixture
def patched_environment(monkeypatch):
    dms = FakeDMS()
    events = FakeEvents()
    lamb = FakeLambda()

    monkeypatch.setattr(orchestrator, "dms", dms)
    monkeypatch.setattr(orchestrator, "events", events)
    monkeypatch.setattr(orchestrator, "lambda_", lamb)
    monkeypatch.setattr(
        orchestrator,
        "_load_config",
        lambda: orchestrator.OrchestratorConfig(
            task_arn="task-arn",
            event_bus="bus",
            runner_function_arn="lambda-arn",
            default_run="2024-01-01",
        ),
    )
    monkeypatch.setattr(orchestrator.uuid, "uuid4", lambda: "job-123")

    return dms, events, lamb


def test_orchestrator_lambda_handler(patched_environment):
    dms, events, lamb = patched_environment

    response = orchestrator.lambda_handler({}, None)

    assert response["statusCode"] == 202
    body = json.loads(response["body"])
    assert body["jobId"] == "job-123"
    assert body["run"] == "2024-01-01"

    assert dms.calls[0]["ReplicationTaskArn"] == "task-arn"

    rule_call = events.put_rule_calls[0]
    assert rule_call["Name"].startswith("sewingmachine-dms-finished-job-123")

    target_call = events.put_targets_calls[0]
    assert target_call["EventBusName"] == "bus"
    target_input = json.loads(target_call["Targets"][0]["Input"])
    assert target_input["cleanupRule"].startswith("sewingmachine-dms-finished-")

    permission = lamb.permissions[0]
    assert permission["SourceArn"] == "arn:rule"
