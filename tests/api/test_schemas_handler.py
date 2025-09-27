import json
from types import SimpleNamespace

import pytest

import src.api.handlers.schemas as handler


def _event(method="GET", origin="http://localhost:5173"):
    payload = {"httpMethod": method}
    if origin:
        payload["headers"] = {"Origin": origin}
    return payload


def _patch_basics(monkeypatch, service_factory):
    settings = SimpleNamespace(allowed_origin="https://awssewingmachine.com,http://localhost:5173", region="us-west-1")
    monkeypatch.setattr(handler, "get_schemas_settings", lambda: settings)
    monkeypatch.setattr(handler, "get_clients", lambda region: object())
    monkeypatch.setattr(handler, "SchemasService", service_factory)


def test_schemas_handler_options(monkeypatch):
    def factory(*_a, **_k):
        raise AssertionError("service should not be created")

    _patch_basics(monkeypatch, factory)

    response = handler.lambda_handler(_event(method="OPTIONS"), None)
    assert response["statusCode"] == 200
    assert response["headers"]["Access-Control-Allow-Methods"] == "GET,OPTIONS"
    assert response["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_schemas_handler_success(monkeypatch):
    class DummyService:
        def __init__(self, *_a, **_k):
            pass

        def execute(self):
            return {"databases": []}

    _patch_basics(monkeypatch, DummyService)

    response = handler.lambda_handler(_event(), None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body == {"databases": []}
    assert response["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"
