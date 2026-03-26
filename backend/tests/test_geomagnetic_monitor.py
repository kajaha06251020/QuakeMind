from app.services.geomagnetic_monitor import get_geomagnetic_info, analyze_geomagnetic


def test_get_info():
    result = get_geomagnetic_info()
    assert result["n_observatories"] > 0


def test_analyze_normal():
    data = [{"timestamp": "2026-03-25T10:00:00Z", "h_nt": 30005.0, "d_nt": 0, "z_nt": 0}]
    result = analyze_geomagnetic(data)
    assert result["anomaly_detected"] is False


def test_analyze_anomaly():
    data = [{"timestamp": "2026-03-25T10:00:00Z", "h_nt": 30200.0, "d_nt": 0, "z_nt": 0}]
    result = analyze_geomagnetic(data)
    assert result["anomaly_detected"] is True


def test_analyze_empty():
    result = analyze_geomagnetic([])
    assert result["anomaly_detected"] is False
