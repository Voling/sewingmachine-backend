from __future__ import annotations

from app.application.health_service import HealthService
from app.config.settings import get_health_settings
from app.presentation.http import build_json_response, build_preflight_response, extract_origin


def lambda_handler(event, _context):
    event = event or {}
    settings = get_health_settings()
    origin = extract_origin(event)

    if event.get("httpMethod") == "OPTIONS":
        return build_preflight_response(settings.allowed_origin, ["OPTIONS", "GET"], request_origin=origin)

    service = HealthService(settings)
    payload = service.execute()
    return build_json_response(200, payload, settings.allowed_origin, ["OPTIONS", "GET"], request_origin=origin)
