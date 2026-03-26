import pytest
import numpy as np
from app.usecases.phase_detection import detect_phases_sta_lta, analyze_waveform, estimate_s_wave


def _synthetic_waveform(duration=30.0, sr=100.0, p_time=10.0):
    n = int(duration * sr)
    t = np.arange(n) / sr
    noise = np.random.default_rng(42).normal(0, 0.1, n)
    signal = np.zeros(n)
    p_idx = int(p_time * sr)
    signal[p_idx:p_idx + int(2 * sr)] = np.sin(2 * np.pi * 5 * t[:int(2 * sr)]) * 2.0
    return noise + signal


def test_detect_p_wave():
    wf = _synthetic_waveform()
    picks = detect_phases_sta_lta(wf, sampling_rate=100.0)
    assert len(picks) >= 1
    assert picks[0]["type"] == "P"
    assert 8.0 < picks[0]["time_sec"] < 12.0


def test_estimate_s_wave():
    p_picks = [{"type": "P", "time_sec": 10.0, "sample": 1000, "sta_lta_ratio": 5.0, "confidence": 0.8}]
    s_picks = estimate_s_wave(p_picks)
    assert len(s_picks) == 1
    assert s_picks[0]["time_sec"] > 10.0


def test_analyze_waveform():
    wf = _synthetic_waveform()
    result = analyze_waveform(wf)
    assert "p_picks" in result
    assert "statistics" in result
    assert result["statistics"]["n_samples"] > 0


def test_no_signal():
    noise = np.random.default_rng(42).normal(0, 0.01, 3000)
    picks = detect_phases_sta_lta(noise, sampling_rate=100.0)
    # Pure noise should have few or no picks
    assert len(picks) <= 2
