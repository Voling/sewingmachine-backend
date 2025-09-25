from __future__ import annotations

from app.application.materialize_service import MaterializeService
from app.config.settings import get_materialize_settings
from app.domain.errors import DomainError
from app.infrastructure.aws_clients import get_clients
from app.presentation.http import build_json_response, build_preflight_response, parse_json
from app.presentation.logging import get_logger


_LOGGER = get_logger("sewingmachine.materialize.handler")
ALLOWED_METHODS = ["OPTIONS", "POST"]


def lambda_handler(event, _context):
    settings = get_materialize_settings()
    method = (event or {}).get("httpMethod", "").upper()
    if method == "OPTIONS":
        return build_preflight_response(settings.allowed_origin, ALLOWED_METHODS)

    try:
        body = parse_json((event or {}).get("body"), default={})
    except ValueError:
        error_payload = {"error": {"code": "BadJson", "message": "Invalid JSON"}}
        return build_json_response(400, error_payload, settings.allowed_origin, ALLOWED_METHODS)

    service = MaterializeService(settings, get_clients(settings.region))

    try:
        result = service.execute(body)
        return build_json_response(200, result, settings.allowed_origin, ALLOWED_METHODS)
    except DomainError as exc:
        return build_json_response(exc.status_code, exc.payload, settings.allowed_origin, ALLOWED_METHODS)
    except Exception:  # pragma: no cover
        _LOGGER.exception("Unhandled materialize error")
        payload = {"error": {"code": "InternalError", "message": "Unexpected failure"}}
        return build_json_response(500, payload, settings.allowed_origin, ALLOWED_METHODS)
