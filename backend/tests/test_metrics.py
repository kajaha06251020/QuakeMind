from app.services.metrics import get_metrics, REQUEST_COUNT, get_content_type


def test_get_metrics():
    REQUEST_COUNT.labels(method="GET", endpoint="/health", status="200").inc()
    output = get_metrics()
    assert b"quakemind_requests_total" in output


def test_content_type():
    ct = get_content_type()
    assert "text/plain" in ct or "openmetrics" in ct.lower() or "text" in ct
