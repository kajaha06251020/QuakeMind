import json
import logging
from app.services.structured_logging import JSONFormatter

def test_json_formatter():
    formatter = JSONFormatter()
    record = logging.LogRecord("test", logging.INFO, "", 0, "hello world", (), None)
    output = formatter.format(record)
    data = json.loads(output)
    assert data["message"] == "hello world"
    assert data["level"] == "INFO"
    assert "timestamp" in data
