"""進化バッチ2のテスト (10モジュール)。"""
import pytest, numpy as np
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord

def _events(n=30):
    import random; random.seed(42)
    base = datetime(2026,1,1,tzinfo=timezone.utc)
    return [EarthquakeRecord(event_id=f"ev2-{i}",magnitude=round(random.uniform(2,6),1),latitude=35+random.uniform(-1,1),longitude=139+random.uniform(-1,1),depth_km=random.uniform(5,50),timestamp=(base+timedelta(days=random.uniform(0,90))).isoformat()) for i in range(n)]

def test_tsunami_sim():
    from app.usecases.tsunami_simulation import simulate_tsunami_propagation
    r = simulate_tsunami_propagation(33.0, 135.0, 8.5, 15.0, grid_size=20, total_minutes=10)
    assert r["tsunami_generated"] is True
    assert r["max_wave_height_m"] > 0

def test_early_warning():
    from app.usecases.early_warning import estimate_from_p_wave
    r = estimate_from_p_wave(100.0, 0.5, 80.0)
    assert r["warning_time_seconds"] > 0
    assert r["estimated_magnitude"] > 0

def test_stress_drop():
    from app.usecases.stress_drop import estimate_stress_drop
    r = estimate_stress_drop(7.0)
    assert r["stress_drop_bar"] > 0
    assert r["category"] in ("very_low","low","normal","high","very_high")

def test_tidal():
    from app.usecases.tidal_triggering import schuster_test
    r = schuster_test(_events(30))
    assert "p_value" in r

def test_ambient_noise():
    from app.usecases.ambient_noise import detect_velocity_change
    r = detect_velocity_change()
    assert r["status"] == "framework_only"

def test_mc_map():
    from app.usecases.mc_mapping import compute_mc_map
    r = compute_mc_map(_events(50), grid_spacing_deg=1.0)
    assert r["n_cells"] >= 0

def test_nowcast():
    from app.usecases.nowcasting import nowcast
    r = nowcast(_events())
    assert r["alert_level"] in ("normal","advisory","elevated")

def test_energy():
    from app.usecases.energy_partition import analyze_energy_partition
    r = analyze_energy_partition([3.0,4.0,5.0,6.0,7.0])
    assert r["max_event_energy_fraction"] > 0.5

def test_source_spectrum():
    from app.usecases.source_spectrum import fit_brune_spectrum
    r = fit_brune_spectrum(6.0)
    assert r["corner_frequency_hz"] > 0

def test_volcano():
    from app.usecases.volcano_seismic import analyze_volcano_seismic
    r = analyze_volcano_seismic(_events())
    assert r["n_analyzed"] == 5
