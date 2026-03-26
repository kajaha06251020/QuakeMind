"""共通テストフィクスチャ。"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.infrastructure.models_db import Base
from app.infrastructure import database


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def db_engine():
    """テスト用 SQLite in-memory エンジン。テストごとにテーブルを再作成する。"""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("PRAGMA foreign_keys = ON"))
    database.override_engine(engine)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    database.override_engine(None)  # type: ignore[arg-type]


@pytest_asyncio.fixture
async def db_session(db_engine):
    """テスト用 DBセッション。"""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def async_client(db_engine):
    """FastAPI async テストクライアント。"""
    from app.interfaces.api import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def client(db_engine):
    """FastAPI sync テストクライアント（既存テスト互換用）。"""
    from fastapi.testclient import TestClient
    from app.interfaces.api import app
    with TestClient(app) as c:
        yield c
