"""Unit tests for predict agent logic."""
import pytest
from agents.predict import _estimate_intensity, _estimate_aftershock_prob, _check_tsunami_risk
from state import compute_severity


# ─── _estimate_intensity ──────────────────────────────────────────────────────

def test_estimate_intensity_typical():
    """M6.0, 深度10km → 震度 5 前後を期待。"""
    result = _estimate_intensity(6.0, 10.0, 100.0)
    assert 4.0 <= result <= 6.5


def test_estimate_intensity_clamp():
    """結果は 0〜7 の範囲に収まる。"""
    assert _estimate_intensity(9.0, 5.0) <= 7.0
    assert _estimate_intensity(1.0, 500.0) >= 0.0


# ─── _estimate_aftershock_prob ────────────────────────────────────────────────

def test_aftershock_prob_range():
    """確率は 0〜1 の範囲。"""
    prob = _estimate_aftershock_prob(5.5, 30.0)
    assert 0.0 <= prob <= 1.0


def test_aftershock_prob_larger_quake_higher():
    """より大きい地震は余震確率が高い。"""
    p_small = _estimate_aftershock_prob(4.0, 30.0)
    p_large = _estimate_aftershock_prob(7.0, 30.0)
    assert p_large > p_small


# ─── _check_tsunami_risk ──────────────────────────────────────────────────────

def test_tsunami_risk_yes():
    assert _check_tsunami_risk(7.0, 30.0) is True


def test_tsunami_risk_no_shallow_small():
    assert _check_tsunami_risk(5.0, 30.0) is False


def test_tsunami_risk_no_deep():
    assert _check_tsunami_risk(7.0, 100.0) is False


# ─── compute_severity ─────────────────────────────────────────────────────────

def test_severity_critical_tsunami():
    assert compute_severity(4.0, 0.1, True) == "CRITICAL"


def test_severity_critical_intensity():
    assert compute_severity(6.5, 0.1, False) == "CRITICAL"


def test_severity_high_intensity():
    assert compute_severity(5.5, 0.1, False) == "HIGH"


def test_severity_high_aftershock():
    assert compute_severity(3.0, 0.7, False) == "HIGH"


def test_severity_medium():
    assert compute_severity(4.5, 0.35, False) == "MEDIUM"


def test_severity_low():
    assert compute_severity(2.0, 0.1, False) == "LOW"


# ─── 重複排除（seen_event_ids） ───────────────────────────────────────────────

def test_dedup_logic():
    """同一 event_id は重複して処理されないことを確認する（ロジックレベル）。"""
    seen = set()
    events = ["evt-001", "evt-002", "evt-001", "evt-003"]
    processed = []
    for eid in events:
        if eid not in seen:
            seen.add(eid)
            processed.append(eid)
    assert processed == ["evt-001", "evt-002", "evt-003"]
