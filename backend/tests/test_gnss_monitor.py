from app.services.gnss_monitor import get_gnss_stations, analyze_displacement


def test_get_stations():
    result = get_gnss_stations()
    assert result["n_stations"] > 0
    assert "reference_url" in result


def test_analyze_normal():
    data = [{"date": "2026-03-25", "east_mm": 0.5, "north_mm": 0.3, "up_mm": 0.1}]
    result = analyze_displacement("940054", data)
    assert result["anomaly_detected"] is False


def test_analyze_anomaly():
    data = [{"date": "2026-03-25", "east_mm": 15.0, "north_mm": 10.0, "up_mm": 5.0}]
    result = analyze_displacement("940054", data)
    assert result["anomaly_detected"] is True


def test_analyze_empty():
    result = analyze_displacement("940054", [])
    assert result["anomaly_detected"] is False
