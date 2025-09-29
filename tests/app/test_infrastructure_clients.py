from unittest.mock import MagicMock

import boto3
import pytest

from app.infrastructure import aws_clients


def test_get_clients_caches_instances(monkeypatch):
    called = {}

    def fake_client(name, region_name=None, config=None):
        called.setdefault(name, 0)
        called[name] += 1
        return MagicMock(name=f"client-{name}")

    monkeypatch.setattr(boto3, "client", fake_client)

    aws_clients.get_clients.cache_clear()
    clients = aws_clients.get_clients("us-west-2")

    clients.dynamodb()
    clients.lambda_()
    clients.dynamodb()

    assert called["dynamodb"] == 1
    assert called["lambda"] == 1

    same_clients = aws_clients.get_clients("us-west-2")
    assert clients is same_clients
