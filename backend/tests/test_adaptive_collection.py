from app.services.adaptive_collection import compute_adaptive_intervals, update_intervals


def test_critical_faster():
    critical = compute_adaptive_intervals("critical")
    normal = compute_adaptive_intervals("normal")
    assert critical["p2p"] < normal["p2p"]


def test_min_max():
    intervals = compute_adaptive_intervals("critical")
    for v in intervals.values():
        assert 10 <= v <= 300


def test_update():
    result = update_intervals("high")
    assert len(result) > 0
