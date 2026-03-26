import pytest
from app.usecases.shakemap import compute_shakemap

def test_shakemap_basic():
    result = compute_shakemap(35.0, 139.0, 10.0, 6.5)
    assert len(result["grid"]) > 0
    assert all("intensity" in p for p in result["grid"])

def test_shakemap_near_source_highest():
    result = compute_shakemap(35.0, 139.0, 10.0, 7.0)
    near = [p for p in result["grid"] if p["distance_km"] < 30]
    far = [p for p in result["grid"] if p["distance_km"] > 200]
    if near and far:
        assert max(p["intensity"] for p in near) > max(p["intensity"] for p in far)

def test_shakemap_small_quake():
    result = compute_shakemap(35.0, 139.0, 50.0, 3.0)
    for p in result["grid"]:
        assert p["intensity"] <= 4.0
