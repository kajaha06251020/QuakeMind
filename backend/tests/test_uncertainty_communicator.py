from app.services.uncertainty_communicator import communicate_risk

def test_high_risk_general():
    result = communicate_risk(0.6, audience="general")
    assert result["message"]["urgency"] == "critical"
    assert "避難" in result["message"]["text"]

def test_low_risk():
    result = communicate_risk(0.01, audience="general")
    assert result["message"]["urgency"] == "normal"

def test_expert():
    result = communicate_risk(0.3, audience="expert")
    assert "%" in result["message"]["text"]

def test_policymaker():
    result = communicate_risk(0.4, audience="policymaker")
    assert "recommended_action" in result["message"]

def test_all_audiences():
    result = communicate_risk(0.5)
    assert "expert" in result["all_audiences"]
    assert "general" in result["all_audiences"]
    assert "policymaker" in result["all_audiences"]
