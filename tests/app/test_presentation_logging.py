from app.presentation.logging import get_logger


def test_get_logger_is_cached():
    logger1 = get_logger("sewingmachine.test")
    logger2 = get_logger("sewingmachine.test")
    assert logger1 is logger2
