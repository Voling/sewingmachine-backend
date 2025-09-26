from __future__ import annotations

from app.application.run_service import RunService
from app.config.settings import get_run_settings
from app.domain.errors import CooldownActiveError, DomainError
from app.infrastructure.aws_clients import get_clients
from app.presentation.http import build_json_response, build_preflight_response, extract_origin, parse_json
from app.presentation.logging import get_logger


_LOGGER = get_logger("sewingmachine.run.handler")
ALLOWED_METHODS = ["OPTIONS", "POST"]


def lambda_handler(event, _context):
    event = event or {}
    settings = get_run_settings()
    method = event.get("httpMethod", "").upper()
    origin = extract_origin(event)

    if method == "OPTIONS":
        return build_preflight_response(settings.allowed_origin, ALLOWED_METHODS, request_origin=origin)

    try:
        body = parse_json(event.get("body"), default={})
    except ValueError:
        error_payload = {"error": {"code": "BadJson", "message": "Invalid JSON body"}}
        return build_json_response(400, error_payload, settings.allowed_origin, ALLOWED_METHODS, request_origin=origin)

    service = RunService(settings, get_clients(settings.region))

    try:
        result = service.execute(body)
        return build_json_response(202, result, settings.allowed_origin, ALLOWED_METHODS, request_origin=origin)
    except CooldownActiveError as exc:
        return build_json_response(exc.status_code, exc.payload, settings.allowed_origin, ALLOWED_METHODS, request_origin=origin)
    except DomainError as exc:
        return build_json_response(exc.status_code, exc.payload, settings.allowed_origin, ALLOWED_METHODS, request_origin=origin)
    except Exception:  # pragma: no cover - defensive
        _LOGGER.exception("Unhandled error while triggering run")
        payload = {"error": {"code": "InternalError", "message": "Unexpected failure"}}
        return build_json_response(500, payload, settings.allowed_origin, ALLOWED_METHODS, request_origin=origin)
