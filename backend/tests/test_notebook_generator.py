from app.services.notebook_generator import generate_research_notebook, generate_daily_notebook


def test_generate_basic():
    md = generate_research_notebook("Test", [{"heading": "Section 1", "content": "Hello"}])
    assert "# Test" in md
    assert "Section 1" in md
    assert "Hello" in md


def test_with_data():
    md = generate_research_notebook("Test", [{"heading": "Data", "content": "", "data": {"key": "value"}}])
    assert "```json" in md
    assert '"key"' in md


def test_daily_notebook():
    md = generate_daily_notebook({"anomaly": {"is_anomalous": True, "p_value": 0.01}})
    assert "異常活動" in md
    assert "日次" in md


def test_empty_daily():
    md = generate_daily_notebook({})
    assert "データなし" in md
