import json
from types import SimpleNamespace

import pytest

import src.api.handlers.run as handler
from app.domain.errors import CooldownActiveError, ValidationError


def _event(method="POST", body=None, origin="http://localhost:5173"):
    payload = {"httpMethod": method, "body": json.dumps(body) if body is not None else body}
    if origin:
        payload["headers"] = {"Origin": origin}
    return payload


def _patch_basics(monkeypatch, service_factory):
    settings = SimpleNamespace(allowed_origin="https://awssewingmachine.com,http://localhost:5173", region="us-west-1")
    monkeypatch.setattr(handler, "get_run_settings", lambda: settings)
    monkeypatch.setattr(handler, "get_clients", lambda region: object())
    monkeypatch.setattr(handler, "RunService", service_factory)


def test_run_handler_options(monkeypatch):
    def factory(*_args, **_kwargs):
        raise AssertionError("service should not be created")

    _patch_basics(monkeypatch, factory)

    response = handler.lambda_handler(_event(method="OPTIONS"), None)
    assert response["statusCode"] == 200
    assert response["headers"]["Access-Control-Allow-Methods"] == "OPTIONS,POST"
    assert response["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_run_handler_bad_json(monkeypatch):
    class DummyService:
        def __init__(self, *_a, **_k):
            pass

    _patch_basics(monkeypatch, DummyService)

    event = {"httpMethod": "POST", "body": "{bad json", "headers": {"Origin": "http://localhost:5173"}}
    response = handler.lambda_handler(event, None)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"]["code"] == "BadJson"
    assert response["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_run_handler_success(monkeypatch):
    class DummyService:
        def __init__(self, *_a, **_k):
            pass

        def execute(self, payload):
            return {"status": "accepted", "payload": payload}

    _patch_basics(monkeypatch, DummyService)

    response = handler.lambda_handler(_event(body={"run": "today"}), None)
    assert response["statusCode"] == 202
    body = json.loads(response["body"])
    assert body["status"] == "accepted"
    assert response["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_run_handler_handles_cooldown(monkeypatch):
    class FailingService:
        def __init__(self, *_a, **_k):
            pass

        def execute(self, payload):
            raise CooldownActiveError(retry_after_seconds=30, run=payload.get("run", "today"), layers={})

    _patch_basics(monkeypatch, FailingService)

    response = handler.lambda_handler(_event(body={"run": "today"}), None)
    assert response["statusCode"] == 429
    body = json.loads(response["body"])
    assert body["retryAfterSeconds"] == 30
    assert response["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_run_handler_handles_domain_error(monkeypatch):
    class FailingService:
        def __init__(self, *_a, **_k):
            pass

        def execute(self, _payload):
            raise ValidationError("nope", code="Bad")

    _patch_basics(monkeypatch, FailingService)

    response = handler.lambda_handler(_event(body={}), None)
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"]["code"] == "Bad"
    assert response["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_run_handler_catches_unexpected(monkeypatch):
    class FailingService:
        def __init__(self, *_a, **_k):
            pass

        def execute(self, _payload):
            raise RuntimeError("boom")

    _patch_basics(monkeypatch, FailingService)

    response = handler.lambda_handler(_event(body={}), None)
    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert body["error"]["code"] == "InternalError"
    assert response["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"
