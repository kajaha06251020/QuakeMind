from app.services.contradiction_resolver import detect_contradictions, resolve_and_explain


def test_detect_contradiction():
    preds = {"etas": {"probability": 0.1, "reliability": 0.8}, "ml": {"probability": 0.7, "reliability": 0.6}}
    contradictions = detect_contradictions(preds)
    assert len(contradictions) >= 1
    assert contradictions[0]["divergence"] > 0.3


def test_no_contradiction():
    preds = {"etas": {"probability": 0.3, "reliability": 0.7}, "ml": {"probability": 0.35, "reliability": 0.6}}
    assert detect_contradictions(preds) == []


def test_resolve():
    preds = {"etas": {"probability": 0.1, "reliability": 0.9}, "ml": {"probability": 0.8, "reliability": 0.3}}
    result = resolve_and_explain(preds)
    assert result["consensus_probability"] > 0
    assert result["contradictions"][0]["preferred_model"] == "etas"
