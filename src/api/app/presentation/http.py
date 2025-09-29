from __future__ import annotations

import json
from typing import Any, Iterable, Sequence


_DEFAULT_ALLOWED_HEADERS = "Content-Type,Authorization"


def build_json_response(
    status_code: int,
    payload: Any,
    allowed_origin: str | Sequence[str],
    allowed_methods: Iterable[str],
    allowed_headers: str = _DEFAULT_ALLOWED_HEADERS,
    request_origin: str | None = None,
) -> dict:
    origin_header = _resolve_origin(allowed_origin, request_origin)
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": origin_header,
            "Access-Control-Allow-Headers": allowed_headers,
            "Access-Control-Allow-Methods": _format_methods(allowed_methods),
        },
        "body": json.dumps(payload),
    }


def build_preflight_response(
    allowed_origin: str | Sequence[str],
    allowed_methods: Iterable[str],
    allowed_headers: str = _DEFAULT_ALLOWED_HEADERS,
    request_origin: str | None = None,
) -> dict:
    origin_header = _resolve_origin(allowed_origin, request_origin)
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": origin_header,
            "Access-Control-Allow-Headers": allowed_headers,
            "Access-Control-Allow-Methods": _format_methods(allowed_methods),
        },
        "body": "",
    }


def parse_json(body: str | None, default: Any) -> Any:
    if body is None or body == "":
        return default
    return json.loads(body)


def extract_origin(event: dict | None) -> str | None:
    if not event:
        return None

    origin = _origin_from_headers(event.get("headers"))
    if origin:
        return origin

    return _origin_from_multi_headers(event.get("multiValueHeaders"))


def _origin_from_multi_headers(headers: Any) -> str | None:
    if not isinstance(headers, dict):
        return None
    for key, value in headers.items():
        if key.lower() != "origin":
            continue
        if isinstance(value, list):
            return value[0] if value else None
        return value
    return None


def _origin_from_headers(headers: Any) -> str | None:
    if isinstance(headers, dict):
        for key, value in headers.items():
            if key.lower() == "origin":
                if isinstance(value, list):
                    return value[0] if value else None
                return value
    return None


def _resolve_origin(allowed_origin: str | Sequence[str], request_origin: str | None) -> str:
    origins = _normalize_origins(allowed_origin)
    if not origins:
        return "*"
    if "*" in origins:
        return "*"
    if request_origin and request_origin in origins:
        return request_origin
    return origins[0]


def _normalize_origins(value: str | Sequence[str]) -> list[str]:
    if isinstance(value, str):
        parts = [segment.strip() for segment in value.split(",")]
        return [part for part in parts if part]
    normalized = []
    for item in value:
        if item:
            normalized.append(str(item).strip())
    return [item for item in normalized if item]


def _format_methods(methods: Iterable[str]) -> str:
    return ",".join(sorted({m.upper() for m in methods}))


def prepare_request(event: dict | str | None, allowed_methods: Iterable[str], allowed_origin: str | Sequence[str]) -> tuple[dict, str | None, dict | None]:
    evt: dict
    if isinstance(event, str):
        evt = json.loads(event)
    elif isinstance(event, dict):
        evt = event
    else:
        evt = {}
    origin = extract_origin(evt)
    method = (evt.get("httpMethod") or "").upper()
    if method == "OPTIONS":
        return evt, origin, build_preflight_response(allowed_origin, allowed_methods, request_origin=origin)
    return evt, origin, None
