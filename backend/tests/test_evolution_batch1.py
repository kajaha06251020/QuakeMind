"""進化バッチ1のテスト (10モジュール)。"""
import pytest, numpy as np
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord

def _events(n=30):
    import random; random.seed(42)
    base = datetime(2026,1,1,tzinfo=timezone.utc)
    return [EarthquakeRecord(event_id=f"ev1-{i}",magnitude=round(random.uniform(2,6),1),latitude=35+random.uniform(-1,1),longitude=139+random.uniform(-1,1),depth_km=random.uniform(5,50),timestamp=(base+timedelta(days=random.uniform(0,90))).isoformat()) for i in range(n)]

def test_site_amplification():
    from app.usecases.site_amplification import compute_site_amplification
    r = compute_site_amplification(5.0, vs30=90)
    assert r["amplified_intensity"] > r["base_intensity"]
    assert r["site_class"] == "soft_soil"

def test_multi_gmpe():
    from app.usecases.multi_gmpe import evaluate_multi_gmpe
    r = evaluate_multi_gmpe(7.0, 50.0)
    assert r["gmpe_results"]["epistemic_uncertainty"] >= 0
    assert len(r["gmpe_results"]) >= 5

def test_spatial_bvalue():
    from app.usecases.spatial_bvalue import compute_spatial_bvalue
    r = compute_spatial_bvalue(_events(50), grid_spacing_deg=1.0)
    assert r["n_cells"] >= 0

def test_moment_rate():
    from app.usecases.moment_rate import compute_moment_rate
    r = compute_moment_rate(_events())
    assert len(r["timeseries"]) > 0

def test_magnitude_conversion():
    from app.usecases.magnitude_conversion import convert_to_mw
    r = convert_to_mw(5.0, "ML")
    assert r["mw"] > 0
    assert convert_to_mw(7.0, "Mw")["mw"] == 7.0

def test_repeaters():
    from app.usecases.repeating_earthquakes import detect_repeaters
    r = detect_repeaters(_events())
    assert "n_repeaters" in r

def test_doublets():
    from app.usecases.doublet_detection import detect_doublets
    r = detect_doublets(_events())
    assert "n_doublets" in r

def test_interevent():
    from app.usecases.interevent_time import analyze_interevent_times
    r = analyze_interevent_times(_events(50))
    assert r["best_model"] in ("exponential", "gamma", "weibull")

def test_csep():
    from app.usecases.model_comparison import csep_comparison
    r = csep_comparison([{"model":"etas","predicted_rate":5.0,"observed_count":4},{"model":"ml","predicted_rate":8.0,"observed_count":4}])
    assert r["best_model"] is not None

def test_aftershock_hazard():
    from app.usecases.aftershock_hazard import compute_aftershock_hazard
    r = compute_aftershock_hazard(_events(), 35.0, 139.0)
    assert "hazard_probabilities" in r
