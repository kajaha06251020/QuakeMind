import numpy as np
from app.usecases.climate_seismicity import analyze_climate_earthquake_correlation

def test_correlation():
    rng = np.random.default_rng(42)
    eq = rng.uniform(50, 100, 30)
    sea = np.linspace(0, 50, 30) + rng.normal(0, 5, 30)
    result = analyze_climate_earthquake_correlation(eq, sea_level_mm=sea)
    assert "correlations" in result
    assert "sea_level" in result["correlations"]

def test_no_climate_data():
    result = analyze_climate_earthquake_correlation(np.array([10, 20, 30, 40, 50]))
    assert result["trends"]["earthquake_rate"]["trend"] in ("increasing", "decreasing", "stable")
