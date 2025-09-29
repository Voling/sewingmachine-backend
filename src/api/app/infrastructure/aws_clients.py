from __future__ import annotations

from functools import lru_cache
from typing import Any
import boto3
from botocore.config import Config
DEFAULT_CLIENT_CONFIG = Config(connect_timeout=3, read_timeout=10)


class AwsClients:
    """Lazy boto3 clients scoped by region."""

    def __init__(self, region: str, *, config: Config | None = None) -> None:
        self._region = region
        self._config = config or DEFAULT_CLIENT_CONFIG
        self._clients: dict[str, Any] = {}

    def dynamodb(self):
        return self._get_client("dynamodb")

    def lambda_(self):
        return self._get_client("lambda")

    def s3(self):
        return self._get_client("s3")

    def athena(self):
        return self._get_client("athena")

    def glue(self):
        return self._get_client("glue")

    def _get_client(self, service: str):
        if service not in self._clients:
            self._clients[service] = boto3.client(service, region_name=self._region, config=self._config)
        return self._clients[service]


@lru_cache(maxsize=4)
def get_clients(region: str, *, config: Config | None = None) -> AwsClients:
    return AwsClients(region, config=config)
