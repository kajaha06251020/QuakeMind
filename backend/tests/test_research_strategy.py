from app.services.research_strategy import recommend_research_strategy

def test_strategy_with_gaps():
    gaps = {"gaps": [{"severity": "high", "type": "data_gap", "description": "データ不足", "recommendation": "データ追加"}]}
    result = recommend_research_strategy(gaps)
    assert result["total_actions"] > 0
    assert result["top_priority"]["priority"] >= 5

def test_strategy_with_model_issues():
    gaps = {"gaps": []}
    scoreboard = {"models": {"bad_model": {"accuracy": 0.3}}}
    result = recommend_research_strategy(gaps, model_scoreboard=scoreboard)
    actions = [a for a in result["action_plan"] if a["category"] == "model_improvement"]
    assert len(actions) > 0

def test_strategy_default():
    result = recommend_research_strategy({"gaps": []})
    assert any(a["category"] == "routine" for a in result["action_plan"])
