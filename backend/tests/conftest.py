"""共通テストフィクスチャ。"""
import pytest
from fastapi.testclient import TestClient

from app.interfaces.api import app


@pytest.fixture
def client():
    """FastAPI TestClient。"""
    with TestClient(app) as c:
        yield c
