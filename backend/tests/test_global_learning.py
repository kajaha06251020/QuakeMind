from app.services.global_learning import search_global_patterns


def test_search_high_risk():
    result = search_global_patterns({"b_value": 0.75, "rate_change_ratio": 2.5, "n_clusters": 4, "max_magnitude": 7.0})
    assert result["most_similar"]["similarity"] > 0.8
    assert len(result["all_matches"]) > 0


def test_search_normal():
    result = search_global_patterns({"b_value": 1.0, "rate_change_ratio": 1.0, "n_clusters": 0, "max_magnitude": 4.0})
    assert result["most_similar"]["name"] == "正常活動パターン"
