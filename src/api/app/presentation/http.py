from __future__ import annotations

import json
from typing import Any, Iterable


def build_json_response(
    status_code: int,
    payload: Any,
    allowed_origin: str,
    allowed_methods: Iterable[str],
    allowed_headers: str = "Content-Type,Authorization",
) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Headers": allowed_headers,
            "Access-Control-Allow-Methods": ",".join(sorted(set(m.upper() for m in allowed_methods))),
        },
        "body": json.dumps(payload),
    }


def build_preflight_response(allowed_origin: str, allowed_methods: Iterable[str], allowed_headers: str = "Content-Type,Authorization") -> dict:
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Headers": allowed_headers,
            "Access-Control-Allow-Methods": ",".join(sorted(set(m.upper() for m in allowed_methods))),
        },
        "body": "",
    }


def parse_json(body: str | None, default: Any) -> Any:
    if body is None or body == "":
        return default
    return json.loads(body)
