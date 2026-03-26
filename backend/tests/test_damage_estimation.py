import pytest
from app.usecases.damage_estimation import estimate_damage

def test_damage_large_near_tokyo():
    result = estimate_damage(35.5, 139.5, 10.0, 7.0)
    assert result["damage_level"] in ("catastrophic", "severe")
    assert result["total_affected_population"] > 0
    cities = [c["city"] for c in result["affected_cities"]]
    assert "東京" in cities

def test_damage_small_remote():
    result = estimate_damage(25.0, 125.0, 50.0, 4.0)
    assert result["damage_level"] in ("negligible", "minor")

def test_damage_has_required_fields():
    result = estimate_damage(35.0, 139.0, 10.0, 6.0)
    assert "damage_level" in result
    assert "total_affected_population" in result
    assert "affected_cities" in result
