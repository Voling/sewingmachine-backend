class DomainError(Exception):
    """Base class for domain specific errors."""

    def __init__(self, code: str, message: str, status_code: int = 400, payload: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.payload = payload or {}


class CooldownActiveError(DomainError):
    def __init__(self, retry_after_seconds: int, run: str, layers: dict):
        payload = {
            "error": {
                "code": "CooldownActive",
                "message": "Full load recently triggered."
            },
            "retryAfterSeconds": retry_after_seconds,
            "run": run,
            "layers": layers,
        }
        super().__init__(code="CooldownActive", message="Cooldown active", status_code=429, payload=payload)


class ValidationError(DomainError):
    def __init__(self, message: str, code: str = "BadRequest", status_code: int = 400):
        payload = {"error": {"code": code, "message": message}}
        super().__init__(code=code, message=message, status_code=status_code, payload=payload)


class ExternalServiceError(DomainError):
    def __init__(self, message: str, code: str = "ExternalServiceError", status_code: int = 502):
        payload = {"error": {"code": code, "message": message}}
        super().__init__(code=code, message=message, status_code=status_code, payload=payload)
