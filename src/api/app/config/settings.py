from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from typing import Optional


@dataclass(frozen=True)
class BaseSettings:
    region: str
    allowed_origin: str


@dataclass(frozen=True)
class RunSettings(BaseSettings):
    orchestrator_function: str
    cooldown_table_name: str
    resource_key: str
    cooldown_seconds: int
    bronze_prefix: Optional[str]
    silver_prefix: Optional[str]
    gold_prefix: Optional[str]
    presign_ttl_seconds: int
    max_dirs_per_layer: int
    max_files_per_dir: int


@dataclass(frozen=True)
class MaterializeSettings(BaseSettings):
    athena_workgroup: str
    athena_output: str


@dataclass(frozen=True)
class QuerySettings(BaseSettings):
    athena_workgroup: str
    athena_output: str
    athena_catalog: str
    default_database: Optional[str]


@dataclass(frozen=True)
class SchemasSettings(BaseSettings):
    pass


@dataclass(frozen=True)
class HealthSettings(BaseSettings):
    service_name: str = "sewingmachine"


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name)
    if value is not None:
        return value
    return default


@lru_cache(maxsize=1)
def get_run_settings() -> RunSettings:
    return RunSettings(
        region=_get_env("AWS_REGION", "us-west-1"),
        allowed_origin=_get_env("ALLOWED_ORIGIN", "*"),
        orchestrator_function=_get_env("ORCHESTRATOR_FN", ""),
        cooldown_table_name=_get_env("DDB_TABLE", ""),
        resource_key=_get_env("RESOURCE_KEY", "full-load"),
        cooldown_seconds=int(_get_env("COOLDOWN_SECONDS", "30")),
        bronze_prefix=_get_env("BRONZE_PREFIX_S3"),
        silver_prefix=_get_env("SILVER_PREFIX_S3"),
        gold_prefix=_get_env("GOLD_PREFIX_S3"),
        presign_ttl_seconds=int(_get_env("PRESIGN_TTL_SECONDS", "900")),
        max_dirs_per_layer=int(_get_env("MAX_DIRS_PER_LAYER", "25")),
        max_files_per_dir=int(_get_env("MAX_FILES_PER_DIR", "50")),
    )


@lru_cache(maxsize=1)
def get_materialize_settings() -> MaterializeSettings:
    return MaterializeSettings(
        region=_get_env("AWS_REGION", "us-west-1"),
        allowed_origin=_get_env("ALLOWED_ORIGIN", "*"),
        athena_workgroup=_get_env("ATHENA_WG", "primary"),
        athena_output=_get_env("ATHENA_OUTPUT", ""),
    )


@lru_cache(maxsize=1)
def get_query_settings() -> QuerySettings:
    return QuerySettings(
        region=_get_env("AWS_REGION", "us-west-1"),
        allowed_origin=_get_env("ALLOWED_ORIGIN", "*"),
        athena_workgroup=_get_env("ATHENA_WG", "primary"),
        athena_output=_get_env("ATHENA_OUTPUT", ""),
        athena_catalog=_get_env("ATHENA_CATALOG", "AwsDataCatalog"),
        default_database=_get_env("ATHENA_DEFAULT_DB"),
    )


@lru_cache(maxsize=1)
def get_schemas_settings() -> SchemasSettings:
    return SchemasSettings(
        region=_get_env("AWS_REGION", "us-west-1"),
        allowed_origin=_get_env("ALLOWED_ORIGIN", "*"),
    )


@lru_cache(maxsize=1)
def get_health_settings() -> HealthSettings:
    return HealthSettings(
        region=_get_env("AWS_REGION", "us-west-1"),
        allowed_origin=_get_env("ALLOWED_ORIGIN", "*"),
        service_name=_get_env("SERVICE_NAME", "sewingmachine"),
    )
