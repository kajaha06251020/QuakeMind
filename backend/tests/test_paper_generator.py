from app.services.paper_generator import generate_paper


def test_generate():
    result = generate_paper("テスト論文", {"b_value": 0.95, "unified_probability": 0.3, "risk_level": "elevated"}, "東京都")
    assert "markdown" in result
    assert "Abstract" in result["markdown"]
    assert result["word_count"] > 50


def test_empty_analyses():
    result = generate_paper("空の分析", {})
    assert "markdown" in result
