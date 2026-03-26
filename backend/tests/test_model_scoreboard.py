from app.services.model_scoreboard import record_score, get_scoreboard, clear_scores

def test_scoreboard():
    clear_scores()
    record_score("etas", 0.8, True)
    record_score("etas", 0.6, False)
    record_score("ml", 0.7, True)
    board = get_scoreboard()
    assert "etas" in board["models"]
    assert "ml" in board["models"]
    assert board["leader"] is not None

def test_ranking():
    clear_scores()
    for _ in range(5):
        record_score("good_model", 0.9, True)
        record_score("bad_model", 0.1, True)  # wrong prediction
    board = get_scoreboard()
    assert board["ranking"][0]["model"] == "good_model"

def test_empty():
    clear_scores()
    board = get_scoreboard()
    assert board["leader"] is None
