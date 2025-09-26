from __future__ import annotations

from app.application.materialize_service import MaterializeService
from app.config.settings import get_materialize_settings
from app.domain.errors import DomainError
from app.infrastructure.aws_clients import get_clients
from app.presentation.http import build_json_response, build_preflight_response, extract_origin, parse_json
from app.presentation.logging import get_logger


_LOGGER = get_logger("sewingmachine.materialize.handler")
ALLOWED_METHODS = ["OPTIONS", "POST"]


def lambda_handler(event, _context):
    event = event or {}
    settings = get_materialize_settings()
    method = event.get("httpMethod", "").upper()
    origin = extract_origin(event)

    if method == "OPTIONS":
        return build_preflight_response(settings.allowed_origin, ALLOWED_METHODS, request_origin=origin)

    try:
        body = parse_json(event.get("body"), default={})
    except ValueError:
        error_payload = {"error": {"code": "BadJson", "message": "Invalid JSON"}}
        return build_json_response(400, error_payload, settings.allowed_origin, ALLOWED_METHODS, request_origin=origin)

    service = MaterializeService(settings, get_clients(settings.region))

    try:
        result = service.execute(body)
        return build_json_response(200, result, settings.allowed_origin, ALLOWED_METHODS, request_origin=origin)
    except DomainError as exc:
        return build_json_response(exc.status_code, exc.payload, settings.allowed_origin, ALLOWED_METHODS, request_origin=origin)
    except Exception:  # pragma: no cover
        _LOGGER.exception("Unhandled materialize error")
        payload = {"error": {"code": "InternalError", "message": "Unexpected failure"}}
        return build_json_response(500, payload, settings.allowed_origin, ALLOWED_METHODS, request_origin=origin)
