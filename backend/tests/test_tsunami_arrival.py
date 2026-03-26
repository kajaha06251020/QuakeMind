import pytest
from app.usecases.tsunami_arrival import estimate_tsunami_arrival

def test_tsunami_large_shallow():
    result = estimate_tsunami_arrival(38.0, 142.0, 20.0, 7.5)
    assert result["tsunami_risk"] is True
    assert len(result["arrivals"]) > 0
    assert result["arrivals"][0]["arrival_minutes"] > 0

def test_tsunami_no_risk_small():
    result = estimate_tsunami_arrival(35.0, 139.0, 10.0, 5.0)
    assert result["tsunami_risk"] is False

def test_tsunami_no_risk_deep():
    result = estimate_tsunami_arrival(35.0, 139.0, 100.0, 7.0)
    assert result["tsunami_risk"] is False

def test_tsunami_sendai_closest_for_offshore_miyagi():
    result = estimate_tsunami_arrival(38.5, 143.0, 15.0, 8.0)
    assert result["tsunami_risk"] is True
    # 仙台が最も近い都市の一つ
    cities = [a["city"] for a in result["arrivals"][:3]]
    assert "仙台" in cities
