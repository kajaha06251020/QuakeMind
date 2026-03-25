"""APIエンドポイントのテスト。"""


def test_get_alerts_empty(client):
    """GET /alerts が正しいスキーマを返すこと。"""
    response = client.get("/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["alerts"], list)


def test_get_alerts_limit_validation(client):
    """GET /alerts?limit=0 は 422 を返すこと。"""
    response = client.get("/alerts?limit=0")
    assert response.status_code == 422


def test_get_alerts_limit_max_validation(client):
    """GET /alerts?limit=101 は 422 を返すこと。"""
    response = client.get("/alerts?limit=101")
    assert response.status_code == 422


def test_get_status(client):
    """GET /status が動作すること。"""
    response = client.get("/status")
    assert response.status_code == 200
