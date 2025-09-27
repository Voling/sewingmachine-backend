from app.domain import errors


def test_cooldown_active_error_payload():
    err = errors.CooldownActiveError(retry_after_seconds=5, run="2024-01-01", layers={})
    assert err.status_code == 429
    assert err.payload["retryAfterSeconds"] == 5


def test_validation_error_defaults():
    err = errors.ValidationError("bad")
    assert err.status_code == 400
    assert err.payload["error"]["code"] == "BadRequest"
