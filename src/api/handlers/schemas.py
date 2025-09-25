from __future__ import annotations

from app.application.schemas_service import SchemasService
from app.config.settings import get_schemas_settings
from app.infrastructure.aws_clients import get_clients
from app.presentation.http import build_json_response, build_preflight_response


ALLOWED_METHODS = ["OPTIONS", "GET"]


def lambda_handler(event, _context):
    settings = get_schemas_settings()
    method = (event or {}).get("httpMethod", "").upper()
    if method == "OPTIONS":
        return build_preflight_response(settings.allowed_origin, ALLOWED_METHODS)

    service = SchemasService(settings, get_clients(settings.region))
    result = service.execute()
    return build_json_response(200, result, settings.allowed_origin, ALLOWED_METHODS)
