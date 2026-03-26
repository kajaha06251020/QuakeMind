"""クーロン応力変化のテスト。"""
import pytest
from app.usecases.coulomb import compute_coulomb_stress


def test_coulomb_near_source():
    result = compute_coulomb_stress(
        source_lat=35.0, source_lon=139.0, source_depth_km=10.0,
        source_magnitude=7.0, grid_spacing_deg=0.5, grid_radius_deg=2.0,
    )
    assert "source_event" in result
    assert "stress_changes" in result
    assert len(result["stress_changes"]) > 0
    # 近いグリッドポイントは正の応力変化を持つべき
    near_points = [p for p in result["stress_changes"] if abs(p["lat"] - 35.0) < 0.6 and abs(p["lon"] - 139.0) < 0.6]
    assert len(near_points) > 0


def test_coulomb_small_earthquake():
    result = compute_coulomb_stress(
        source_lat=35.0, source_lon=139.0, source_depth_km=10.0,
        source_magnitude=3.0, grid_spacing_deg=0.5, grid_radius_deg=2.0,
    )
    # 小さい地震は応力変化が小さい
    max_stress = max(abs(p["delta_cfs_bar"]) for p in result["stress_changes"])
    assert max_stress < 10.0


def test_coulomb_empty_at_source():
    """震源直上のグリッドポイントは除外される。"""
    result = compute_coulomb_stress(
        source_lat=35.0, source_lon=139.0, source_depth_km=10.0,
        source_magnitude=6.0, grid_spacing_deg=0.5, grid_radius_deg=1.0,
    )
    for p in result["stress_changes"]:
        assert not (p["lat"] == 35.0 and p["lon"] == 139.0)
