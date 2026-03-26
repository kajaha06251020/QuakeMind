from app.services.traffic_info import get_traffic_info_urls, estimate_road_impact


def test_traffic_urls():
    result = get_traffic_info_urls()
    assert "jartic_url" in result
    assert len(result["nexco_urls"]) == 3


def test_impact_critical():
    result = estimate_road_impact(6.5)
    assert result["impact_level"] == "critical"


def test_impact_minimal():
    result = estimate_road_impact(3.0)
    assert result["impact_level"] == "minimal"
    assert result["expected_closures"] == []
