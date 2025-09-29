from __future__ import annotations

from app.application.run_service import RunService
from app.config.settings import get_run_settings
from app.domain.errors import CooldownActiveError, DomainError
from app.infrastructure.aws_clients import get_clients
from app.presentation.http import prepare_request, build_json_response, build_preflight_response, extract_origin, parse_json
from app.presentation.logging import get_logger


_LOGGER = get_logger("sewingmachine.run.handler")
ALLOWED_METHODS = ["OPTIONS", "POST"]


def lambda_handler(event, _context):
    settings = get_run_settings()
    event_obj, origin, preflight = prepare_request(event, ALLOWED_METHODS, settings.allowed_origin)
    if preflight:
        return preflight


    try:
        body = parse_json(event_obj.get("body"), default={})
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
