import json
from types import SimpleNamespace

import pytest

import src.api.handlers.materialize as handler
from app.domain.errors import ValidationError


def _event(method="POST", body=None, origin="http://localhost:5173"):
    payload = {"httpMethod": method, "body": json.dumps(body) if body is not None else body}
    if origin:
        payload["headers"] = {"Origin": origin}
    return payload


def _patch_basics(monkeypatch, service_factory):
    settings = SimpleNamespace(allowed_origin="https://awssewingmachine.com,http://localhost:5173", region="us-west-1")
    monkeypatch.setattr(handler, "get_materialize_settings", lambda: settings)
    monkeypatch.setattr(handler, "get_clients", lambda region: object())
    monkeypatch.setattr(handler, "MaterializeService", service_factory)


def test_materialize_handler_options(monkeypatch):
    def factory(*_a, **_k):
        raise AssertionError("service should not be created")

    _patch_basics(monkeypatch, factory)

    response = handler.lambda_handler(_event(method="OPTIONS"), None)
    assert response["statusCode"] == 200
    assert response["headers"]["Access-Control-Allow-Methods"] == "OPTIONS,POST"
    assert response["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_materialize_handler_bad_json(monkeypatch):
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


def test_materialize_handler_success(monkeypatch):
    class DummyService:
        def __init__(self, *_a, **_k):
            pass

        def execute(self, payload):
            return {"status": "ok", "payload": payload}

    _patch_basics(monkeypatch, DummyService)

    response = handler.lambda_handler(_event(body={"mode": "append"}), None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "ok"
    assert response["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_materialize_handler_domain_error(monkeypatch):
    class FailingService:
        def __init__(self, *_a, **_k):
            pass

        def execute(self, _payload):
            raise ValidationError("invalid", code="Bad")

    _patch_basics(monkeypatch, FailingService)

    response = handler.lambda_handler(_event(body={}), None)
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"]["code"] == "Bad"
    assert response["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_materialize_handler_unexpected(monkeypatch):
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
