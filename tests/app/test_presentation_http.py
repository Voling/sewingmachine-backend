from app.presentation import http


def test_build_json_response_contains_headers():
    response = http.build_json_response(200, {"ok": True}, "*", ["GET", "POST"])
    assert response["statusCode"] == 200
    assert "application/json" in response["headers"]["Content-Type"]
    assert "GET" in response["headers"]["Access-Control-Allow-Methods"]
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"


def test_build_preflight_response():
    response = http.build_preflight_response("*", ["OPTIONS"])
    assert response["statusCode"] == 200
    assert "OPTIONS" in response["headers"]["Access-Control-Allow-Methods"]


def test_build_json_response_selects_matching_origin():
    response = http.build_json_response(
        200,
        {"ok": True},
        "https://awssewingmachine.com,http://localhost:5173",
        ["POST"],
        request_origin="http://localhost:5173",
    )
    assert response["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_build_json_response_falls_back_to_first_origin():
    response = http.build_json_response(
        200,
        {"ok": True},
        ["https://awssewingmachine.com", "http://localhost:5173"],
        ["POST"],
        request_origin="https://unknown",
    )
    assert response["headers"]["Access-Control-Allow-Origin"] == "https://awssewingmachine.com"


def test_extract_origin_prefers_headers():
    event = {"headers": {"Origin": "http://localhost:5173"}}
    assert http.extract_origin(event) == "http://localhost:5173"


def test_extract_origin_reads_multi_value_headers():
    event = {"multiValueHeaders": {"origin": ["http://localhost:5173", "https://other"]}}
    assert http.extract_origin(event) == "http://localhost:5173"


def test_parse_json_returns_default():
    assert http.parse_json(None, default={"x": 1}) == {"x": 1}


def test_prepare_request_returns_event_and_origin():
    event, origin, preflight = http.prepare_request({"httpMethod": "GET", "headers": {"Origin": "http://example"}}, ["GET"], "http://example")
    assert origin == "http://example"
    assert preflight is None
    assert event["httpMethod"] == "GET"


def test_prepare_request_handles_options():
    _event = {"httpMethod": "OPTIONS", "headers": {"Origin": "http://localhost"}}
    event, origin, preflight = http.prepare_request(_event, ["OPTIONS", "POST"], "http://localhost")
    assert origin == "http://localhost"
    assert preflight["statusCode"] == 200
    assert event["httpMethod"] == "OPTIONS"
