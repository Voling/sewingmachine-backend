import datetime
from types import SimpleNamespace

import pytest
from botocore.exceptions import ClientError

from app.application.run_service import RunService
from app.config.settings import RunSettings
from app.domain.errors import CooldownActiveError


class FakePaginator:
    def __init__(self, parent):
        self._parent = parent

    def paginate(self, **kwargs):
        if kwargs.get("Delimiter") == "/":
            pages = self._parent.dir_pages
        else:
            pages = self._parent.file_pages
        for page in pages:
            yield page


class FakeDynamo:
    def __init__(self):
        self.put_calls = []
        self.raise_conditional = False
        self.current_item = None

    def put_item(self, **kwargs):
        self.put_calls.append(kwargs)
        if self.raise_conditional:
            raise ClientError(
                {
                    "Error": {
                        "Code": "ConditionalCheckFailedException",
                        "Message": "condition failed",
                    }
                },
                "PutItem",
            )

    def get_item(self, **_kwargs):
        return {"Item": self.current_item or {}}


class FakeLambda:
    def __init__(self):
        self.invocations = []

    def invoke(self, **kwargs):
        self.invocations.append(kwargs)


class FakeS3:
    def __init__(self, dir_pages=None, file_pages=None):
        self.dir_pages = dir_pages or [{"CommonPrefixes": []}]
        self.file_pages = file_pages or [{"Contents": []}]
        self.presigned = []

    def get_paginator(self, name):
        if name != "list_objects_v2":  # pragma: no cover - defensive guard
            raise NotImplementedError(name)
        return FakePaginator(self)

    def generate_presigned_url(self, **kwargs):
        self.presigned.append(kwargs)
        return "https://signed"


class FakeClients:
    def __init__(self, ddb=None, lam=None, s3=None):
        self._ddb = ddb or FakeDynamo()
        self._lambda = lam or FakeLambda()
        self._s3 = s3 or FakeS3()

    def dynamodb(self):
        return self._ddb

    def lambda_(self):
        return self._lambda

    def s3(self):
        return self._s3


RUN_SETTINGS = RunSettings(
    region="us-west-1",
    allowed_origin="*",
    orchestrator_function="orchestrator",
    cooldown_table_name="cooldowns",
    resource_key="resource",
    cooldown_seconds=30,
    bronze_prefix="s3://bucket/bronze/{run}/",
    silver_prefix=None,
    gold_prefix=None,
    presign_ttl_seconds=60,
    max_dirs_per_layer=25,
    max_files_per_dir=50,
)


def test_run_service_happy_path(monkeypatch):
    s3 = FakeS3(
        dir_pages=[{"CommonPrefixes": []}],
        file_pages=[
            {
                "Contents": [
                    {
                        "Key": "bronze/2024-01-01/file.parquet",
                        "Size": 10,
                        "LastModified": datetime.datetime(2024, 1, 1, 0, 0),
                    }
                ]
            }
        ],
    )
    clients = FakeClients(s3=s3)

    monkeypatch.setattr(
        "app.application.run_service.time",
        SimpleNamespace(time=lambda: 1_000, sleep=lambda *_: None),
    )

    service = RunService(RUN_SETTINGS, clients)
    payload = {"run": "2024-01-01"}

    result = service.execute(payload)

    assert result["status"] == "accepted"
    assert result["run"] == "2024-01-01"
    assert result["layers"]["bronze"]["dir_count"] == 1
    assert clients._lambda.invocations[0]["FunctionName"] == "orchestrator"
    assert clients._s3.presigned[0]["Params"]["Key"] == "bronze/2024-01-01/file.parquet"


def test_run_service_cooldown_active(monkeypatch):
    ddb = FakeDynamo()
    ddb.raise_conditional = True
    ddb.current_item = {"allowAfter": {"N": "1300"}}

    clients = FakeClients(ddb=ddb)

    monkeypatch.setattr(
        "app.application.run_service.time",
        SimpleNamespace(time=lambda: 1_200, sleep=lambda *_: None),
    )

    service = RunService(RUN_SETTINGS, clients)

    with pytest.raises(CooldownActiveError) as exc_info:
        service.execute({"run": "2024-01-02"})

    assert exc_info.value.payload["retryAfterSeconds"] == 100
    assert not clients._lambda.invocations
