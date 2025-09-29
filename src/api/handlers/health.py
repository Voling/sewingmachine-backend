from __future__ import annotations

from app.application.health_service import HealthService
from app.config.settings import get_health_settings
from app.presentation.http import prepare_request, build_json_response, build_preflight_response, extract_origin


def lambda_handler(event, _context):
    settings = get_health_settings()
    event_obj, origin, preflight = prepare_request(event, ["OPTIONS", "GET"], settings.allowed_origin)
    if preflight:
        return preflight

    service = HealthService(settings)
    payload = service.execute()
    return build_json_response(200, payload, settings.allowed_origin, ["OPTIONS", "GET"], request_origin=origin)
