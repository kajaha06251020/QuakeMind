from app.services.scenario_db import precompute_scenarios, get_cached_scenario, find_nearest_scenario


def test_precompute():
    result = precompute_scenarios()
    assert result["total_cached"] > 0


def test_get_cached():
    precompute_scenarios()
    s = get_cached_scenario("nankai_m9")
    assert s is not None
    assert s["impact_level"] == "catastrophic"


def test_find_nearest():
    precompute_scenarios()
    result = find_nearest_scenario(33.0, 135.0, 8.5)
    assert result is not None
