from app.services.pattern_memory import store_pattern, find_similar_patterns, get_all_patterns, clear_patterns

def test_store_and_find():
    clear_patterns()
    store_pattern("cluster_a", [1.0, 0.0, 0.0])
    store_pattern("cluster_b", [0.0, 1.0, 0.0])
    results = find_similar_patterns([0.9, 0.1, 0.0])
    assert len(results) >= 1
    assert results[0]["name"] == "cluster_a"

def test_find_empty():
    clear_patterns()
    assert find_similar_patterns([1.0, 0.0]) == []

def test_get_all():
    clear_patterns()
    store_pattern("p1", [1, 2, 3])
    assert len(get_all_patterns()) == 1
