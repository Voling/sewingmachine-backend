import json
from types import SimpleNamespace

import pytest

import src.api.handlers.health as handler


def _event(method="GET", origin="http://localhost:5173"):
    payload = {"httpMethod": method}
    if origin:
        payload["headers"] = {"Origin": origin}
    return payload


def _patch_settings(monkeypatch):
    settings = SimpleNamespace(allowed_origin="https://awssewingmachine.com,http://localhost:5173", region="us-west-1", service_name="sewingmachine")
    monkeypatch.setattr(handler, "get_health_settings", lambda: settings)


def test_health_handler_options(monkeypatch):
    _patch_settings(monkeypatch)
    response = handler.lambda_handler(_event(method="OPTIONS"), None)
    assert response["statusCode"] == 200
    assert response["headers"]["Access-Control-Allow-Methods"] == "GET,OPTIONS"
    assert response["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_health_handler_success(monkeypatch):
    _patch_settings(monkeypatch)

    response = handler.lambda_handler(_event(), None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "ok"
    assert body["service"] == "sewingmachine"
    assert response["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"
