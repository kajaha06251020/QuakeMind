import pytest
from app.usecases.scenario_engine import simulate_scenario, run_preset_scenario, PRESET_SCENARIOS


def test_scenario_m9():
    result = simulate_scenario(33.0, 135.0, 9.0, 15.0, "南海テスト")
    assert result["impact_level"] == "catastrophic"
    assert result["tsunami"]["risk"] is True
    assert result["damage"]["affected_population"] > 0


def test_scenario_m5():
    result = simulate_scenario(35.0, 139.0, 5.0, 10.0)
    assert result["impact_level"] in ("moderate", "significant")


def test_preset_scenarios():
    for key in PRESET_SCENARIOS:
        result = run_preset_scenario(key)
        assert "impact_level" in result
        assert "summary" in result


def test_preset_invalid():
    result = run_preset_scenario("nonexistent")
    assert "error" in result
