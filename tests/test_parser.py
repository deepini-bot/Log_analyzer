from app.parser import parse_logs, normalize_message

def test_parse_structured_line():
    rows = parse_logs("2026-01-01 10:00:00 ERROR api: database timeout id=123")
    assert len(rows) == 1
    assert rows[0]["level"] == "ERROR"
    assert rows[0]["service"] == "api"

def test_parse_bracketed_timestamp_and_service():
    row = parse_logs("[2026-01-01 10:00:00] [ERROR] [api] Request 503 failed")[0]
    assert row["timestamp"] == "2026-01-01 10:00:00"
    assert row["level"] == "ERROR"
    assert row["service"] == "api"
    assert row["message"] == "Request 503 failed"

def test_normalize_numbers():
    assert normalize_message("request failed id=123") == normalize_message("request failed id=999")
