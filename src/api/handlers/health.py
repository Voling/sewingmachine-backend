from __future__ import annotations

from app.config.settings import get_health_settings
from app.application.health_service import HealthService
from app.presentation.http import build_json_response, build_preflight_response


def lambda_handler(event, _context):
    settings = get_health_settings()
    if (event or {}).get("httpMethod") == "OPTIONS":
        return build_preflight_response(settings.allowed_origin, ["OPTIONS", "GET"])

    service = HealthService(settings)
    payload = service.execute()
    return build_json_response(200, payload, settings.allowed_origin, ["OPTIONS", "GET"])
