import os
from app.config import settings


def test_get_run_settings_reads_env(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("ALLOWED_ORIGIN", "https://example.com")
    monkeypatch.setenv("ORCHESTRATOR_FN", "orchestrator")
    monkeypatch.setenv("DDB_TABLE", "cooldowns")
    monkeypatch.setenv("RESOURCE_KEY", "full-load")
    monkeypatch.setenv("COOLDOWN_SECONDS", "45")
    monkeypatch.setenv("PRESIGN_TTL_SECONDS", "120")
    monkeypatch.setenv("MAX_DIRS_PER_LAYER", "5")
    monkeypatch.setenv("MAX_FILES_PER_DIR", "7")

    settings.get_run_settings.cache_clear()
    run_settings = settings.get_run_settings()

    assert run_settings.region == "us-east-1"
    assert run_settings.allowed_origin == "https://example.com"
    assert run_settings.orchestrator_function == "orchestrator"
    assert run_settings.cooldown_seconds == 45
    assert run_settings.presign_ttl_seconds == 120
    assert run_settings.max_dirs_per_layer == 5
    assert run_settings.max_files_per_dir == 7


def test_get_query_settings_defaults(monkeypatch):
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGIN", raising=False)
    settings.get_query_settings.cache_clear()
    query_settings = settings.get_query_settings()

    assert query_settings.region == "us-west-1"
    assert query_settings.allowed_origin == "*"
    assert query_settings.athena_catalog == "AwsDataCatalog"
