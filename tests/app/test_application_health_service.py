from app.application.health_service import HealthService
from app.config.settings import HealthSettings


def test_health_service_execute_returns_status(monkeypatch):
    settings = HealthSettings(region="us-west-2", allowed_origin="https://origin", service_name="svc")
    service = HealthService(settings)

    payload = service.execute()

    assert payload["status"] == "ok"
    assert payload["service"] == "svc"
    assert payload["time"].endswith("Z")
