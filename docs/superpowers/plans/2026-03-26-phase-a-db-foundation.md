# Phase A: データベース基盤 — PostgreSQL移行 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SQLite を SQLAlchemy async + Alembic + PostgreSQL に移行し、全地震イベント保存・ユーザー設定テーブルを追加する。

**Architecture:** `database.py` が async engine/session を管理、`models_db.py` が4つの SQLAlchemy モデルを定義、`db.py` を SQLAlchemy クエリに全面書き換え。Alembic でマイグレーション管理。テストは SQLite in-memory。

**Tech Stack:** SQLAlchemy 2.x (async), asyncpg, Alembic, PostgreSQL 16, pytest-asyncio, httpx (AsyncClient)

**Spec:** `docs/superpowers/specs/2026-03-26-phase-a-db-foundation-design.md`

---

## 変更後ファイル構成

```
backend/
├── app/
│   ├── config.py                       # (変更) database_url 追加、db_path 削除
│   ├── infrastructure/
│   │   ├── database.py                 # (新規) async engine + sessionmaker + get_session
│   │   ├── models_db.py               # (新規) SQLAlchemy テーブルモデル4つ
│   │   ├── db.py                      # (変更) aiosqlite → SQLAlchemy 全面書き換え
│   │   └── multi_source.py            # (変更) event_store.save_events() 呼び出し追加
│   ├── usecases/
│   │   └── event_store.py             # (新規) イベント全件保存ロジック
│   └── interfaces/
│       └── api.py                     # (変更) lifespan変更、新規エンドポイント3つ
├── tests/
│   ├── conftest.py                    # (変更) async対応、SQLAlchemy session fixture
│   ├── test_database.py              # (新規)
│   ├── test_event_store.py           # (新規)
│   ├── test_events_api.py            # (新規)
│   ├── test_settings_api.py          # (新規)
│   └── (既存テスト)                   # conftest.py 変更で対応
├── alembic/
│   ├── env.py                        # (新規)
│   └── versions/
│       └── 001_initial.py            # (新規)
├── alembic.ini                       # (新規)
├── requirements.txt                  # (変更)
└── docker-compose.yml               # (変更、ルートにある)
```

---

## Task 1: 依存追加 + config変更

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`

- [ ] **Step 1.1: requirements.txt に依存を追加する**

`backend/requirements.txt` 末尾に追記:

```
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0
greenlet>=3.0.0
```

- [ ] **Step 1.2: pip install する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/pip install "sqlalchemy[asyncio]>=2.0.0" "asyncpg>=0.29.0" "alembic>=1.13.0" "greenlet>=3.0.0"
```

- [ ] **Step 1.3: config.py を変更する**

`backend/app/config.py` の `Settings` クラスで:
- `db_path` を削除
- 以下を追加（`llm_provider` の前に配置）:

```python
    # データベース
    database_url: str = "postgresql+asyncpg://quakemind:quakemind_dev@localhost:5432/quakemind"
    database_url_test: str = "sqlite+aiosqlite://"
```

- [ ] **Step 1.4: コミット**

```bash
git add backend/requirements.txt backend/app/config.py
git commit -m "chore: add SQLAlchemy/asyncpg/Alembic deps, update config"
```

---

## Task 2: SQLAlchemy モデル + database.py

**Files:**
- Create: `backend/app/infrastructure/database.py`
- Create: `backend/app/infrastructure/models_db.py`
- Create: `backend/tests/test_database.py`

- [ ] **Step 2.1: テストを作成する**

`backend/tests/test_database.py` を作成:

```python
"""database.py + models_db.py のテスト。"""
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.infrastructure.models_db import Base, EarthquakeEventDB, AlertDB, SeenEventDB, UserSettingsDB


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("PRAGMA foreign_keys = ON"))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_earthquake_event(session: AsyncSession):
    event = EarthquakeEventDB(
        id=uuid.uuid4(),
        event_id="test-001",
        source="p2p",
        magnitude=5.0,
        depth_km=10.0,
        latitude=35.68,
        longitude=139.76,
        region="東京都",
        occurred_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
    )
    session.add(event)
    await session.commit()

    result = await session.execute(select(EarthquakeEventDB).where(EarthquakeEventDB.event_id == "test-001"))
    row = result.scalar_one()
    assert row.magnitude == 5.0
    assert row.region == "東京都"


@pytest.mark.asyncio
async def test_earthquake_event_unique_constraint(session: AsyncSession):
    """同じ event_id の二重挿入は IntegrityError。"""
    from sqlalchemy.exc import IntegrityError

    now = datetime.now(timezone.utc)
    for _ in range(2):
        session.add(EarthquakeEventDB(
            id=uuid.uuid4(), event_id="dup-001", source="p2p",
            magnitude=5.0, depth_km=10.0, latitude=35.0, longitude=139.0,
            region="テスト", occurred_at=now, fetched_at=now,
        ))
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_create_alert_with_fk(session: AsyncSession):
    """alerts は earthquake_events の event_id を参照する。"""
    now = datetime.now(timezone.utc)
    event = EarthquakeEventDB(
        id=uuid.uuid4(), event_id="ev-001", source="usgs",
        magnitude=6.0, depth_km=30.0, latitude=35.0, longitude=139.0,
        region="大阪府", occurred_at=now, fetched_at=now,
    )
    session.add(event)
    await session.flush()

    alert = AlertDB(
        id=uuid.uuid4(), event_id="ev-001", severity="HIGH",
        ja_text="テスト", en_text="Test", is_fallback=False,
        risk_json=None, route_json=None, created_at=now,
    )
    session.add(alert)
    await session.commit()

    result = await session.execute(select(AlertDB).where(AlertDB.event_id == "ev-001"))
    row = result.scalar_one()
    assert row.severity == "HIGH"


@pytest.mark.asyncio
async def test_create_user_settings(session: AsyncSession):
    now = datetime.now(timezone.utc)
    settings = UserSettingsDB(
        id=uuid.uuid4(), user_id="default",
        min_severity="LOW", region_filters=[], notification_channels=[],
        created_at=now, updated_at=now,
    )
    session.add(settings)
    await session.commit()

    result = await session.execute(select(UserSettingsDB).where(UserSettingsDB.user_id == "default"))
    row = result.scalar_one()
    assert row.min_severity == "LOW"
```

- [ ] **Step 2.2: テストが失敗することを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_database.py -v
```

期待: FAILED（`models_db` が存在しない）

- [ ] **Step 2.3: models_db.py を作成する**

`backend/app/infrastructure/models_db.py` を作成:

```python
"""SQLAlchemy テーブルモデル定義。"""
import uuid
from datetime import datetime

from sqlalchemy import String, Float, Boolean, Text, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EarthquakeEventDB(Base):
    __tablename__ = "earthquake_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    magnitude: Mapped[float] = mapped_column(Float, nullable=False)
    depth_km: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    region: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_events_occurred_at", "occurred_at"),
        Index("ix_events_region", "region"),
        Index("ix_events_magnitude", "magnitude"),
    )


class AlertDB(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(
        String, ForeignKey("earthquake_events.event_id"), unique=True, nullable=False
    )
    severity: Mapped[str] = mapped_column(String, nullable=False)
    ja_text: Mapped[str] = mapped_column(Text, nullable=False)
    en_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    route_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_alerts_created_at", "created_at"),
        Index("ix_alerts_severity", "severity"),
    )


class SeenEventDB(Base):
    __tablename__ = "seen_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserSettingsDB(Base):
    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    min_severity: Mapped[str] = mapped_column(String, default="LOW")
    region_filters: Mapped[list] = mapped_column(JSON, default=list)
    notification_channels: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

- [ ] **Step 2.4: database.py を作成する**

`backend/app/infrastructure/database.py` を作成:

```python
"""非同期 DB エンジンとセッション管理。"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine

from app.config import settings
from app.infrastructure.models_db import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_db() -> None:
    """テスト・開発用: metadata から全テーブルを作成する。本番では Alembic を使う。"""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def override_engine(engine: AsyncEngine) -> None:
    """テスト用: エンジンを差し替える。"""
    global _engine, _session_factory
    _engine = engine
    _session_factory = async_sessionmaker(engine, expire_on_commit=False)
```

- [ ] **Step 2.5: テストがパスすることを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_database.py -v
```

期待: 4件 PASSED

- [ ] **Step 2.6: コミット**

```bash
git add backend/app/infrastructure/database.py backend/app/infrastructure/models_db.py backend/tests/test_database.py
git commit -m "feat(infra): add SQLAlchemy models and async database engine"
```

---

## Task 3: db.py を SQLAlchemy に全面書き換え

**Files:**
- Modify: `backend/app/infrastructure/db.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 3.1: conftest.py を async 対応に書き換える**

`backend/tests/conftest.py` を以下に置き換え:

```python
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
```

- [ ] **Step 3.2: db.py を全面書き換える**

`backend/app/infrastructure/db.py` を以下に置き換え:

```python
"""データベースアクセスレイヤー（SQLAlchemy async）。"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, delete

from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import SeenEventDB, AlertDB, EarthquakeEventDB, UserSettingsDB
from app.domain.models import AlertMessage, RiskScore, EvacuationRoute

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """互換用: database.init_db() を呼ぶ。"""
    from app.infrastructure.database import init_db as _init
    await _init()


async def is_event_seen(event_id: str) -> bool:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(SeenEventDB.event_id).where(SeenEventDB.event_id == event_id)
        )
        return result.scalar_one_or_none() is not None


async def mark_event_seen(event_id: str) -> None:
    factory = get_session_factory()
    async with factory() as session:
        existing = await session.execute(
            select(SeenEventDB).where(SeenEventDB.event_id == event_id)
        )
        if existing.scalar_one_or_none() is None:
            session.add(SeenEventDB(
                event_id=event_id,
                seen_at=datetime.now(timezone.utc),
            ))
            await session.commit()


async def save_alert(
    alert: AlertMessage,
    risk: Optional[RiskScore] = None,
    route: Optional[EvacuationRoute] = None,
) -> None:
    factory = get_session_factory()
    async with factory() as session:
        # 既存アラートを削除（UPSERT の代替）
        await session.execute(
            delete(AlertDB).where(AlertDB.event_id == alert.event_id)
        )
        session.add(AlertDB(
            id=uuid.uuid4(),
            event_id=alert.event_id,
            severity=alert.severity,
            ja_text=alert.ja_text,
            en_text=alert.en_text,
            is_fallback=alert.is_fallback,
            created_at=alert.timestamp,
            risk_json=risk.model_dump() if risk else None,
            route_json=route.model_dump(mode="json") if route else None,
        ))
        await session.commit()


async def get_latest_alert() -> Optional[dict]:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(AlertDB).order_by(AlertDB.created_at.desc()).limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return {
            "event_id": row.event_id,
            "severity": row.severity,
            "ja_text": row.ja_text,
            "en_text": row.en_text,
            "is_fallback": row.is_fallback,
            "timestamp": row.created_at.isoformat() if row.created_at else None,
            "risk_json": row.risk_json,
            "route_json": row.route_json,
        }


async def get_db_status() -> dict:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(func.count()).select_from(AlertDB))
        total = result.scalar_one()
        latest = await get_latest_alert()
    return {"total_alerts": total, "latest": latest}


async def get_alert_locations(limit: int = 50) -> list[dict]:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(AlertDB).order_by(AlertDB.created_at.desc()).limit(limit)
        )
        rows = result.scalars().all()

    locations = []
    for row in rows:
        route = row.route_json
        if not route:
            continue
        lat = route.get("latitude") if isinstance(route, dict) else None
        lon = route.get("longitude") if isinstance(route, dict) else None
        if lat is None or lon is None:
            continue
        locations.append({
            "event_id": row.event_id,
            "severity": row.severity,
            "timestamp": row.created_at.isoformat() if row.created_at else None,
            "latitude": lat,
            "longitude": lon,
            "danger_radius_km": route.get("danger_radius_km"),
        })
    return locations


async def get_alerts(limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
    factory = get_session_factory()
    async with factory() as session:
        total_result = await session.execute(select(func.count()).select_from(AlertDB))
        total = total_result.scalar_one()
        result = await session.execute(
            select(AlertDB).order_by(AlertDB.created_at.desc()).limit(limit).offset(offset)
        )
        rows = result.scalars().all()
    return [
        {
            "event_id": r.event_id,
            "severity": r.severity,
            "ja_text": r.ja_text,
            "en_text": r.en_text,
            "is_fallback": r.is_fallback,
            "timestamp": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ], total
```

- [ ] **Step 3.3: 既存テストがパスすることを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_api.py tests/test_agents.py -v
```

期待: 全件 PASSED

- [ ] **Step 3.4: コミット**

```bash
git add backend/app/infrastructure/db.py backend/tests/conftest.py
git commit -m "refactor(db): migrate from aiosqlite to SQLAlchemy async"
```

---

## Task 4: event_store.py（イベント全件保存）

**Files:**
- Create: `backend/app/usecases/event_store.py`
- Create: `backend/tests/test_event_store.py`

- [ ] **Step 4.1: テストを作成する**

`backend/tests/test_event_store.py` を作成:

```python
"""event_store のテスト。"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone

from app.domain.models import EarthquakeEvent
from app.usecases.event_store import save_events
from app.infrastructure.models_db import EarthquakeEventDB
from sqlalchemy import select


@pytest.mark.asyncio
async def test_save_events_basic(db_session):
    """イベントが保存されること。"""
    events = [
        EarthquakeEvent(
            event_id="ev-001", magnitude=5.0, depth_km=10.0,
            latitude=35.0, longitude=139.0, region="東京都",
            timestamp=datetime.now(timezone.utc), source="p2p",
        ),
    ]
    count = await save_events(events)
    assert count == 1

    result = await db_session.execute(select(EarthquakeEventDB))
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].event_id == "ev-001"


@pytest.mark.asyncio
async def test_save_events_duplicates_ignored(db_session):
    """同じ event_id は無視される。"""
    event = EarthquakeEvent(
        event_id="ev-dup", magnitude=5.0, depth_km=10.0,
        latitude=35.0, longitude=139.0, region="東京都",
        timestamp=datetime.now(timezone.utc), source="p2p",
    )
    count1 = await save_events([event])
    count2 = await save_events([event])
    assert count1 == 1
    assert count2 == 0


@pytest.mark.asyncio
async def test_save_events_empty_list(db_session):
    """空リストは0件。"""
    count = await save_events([])
    assert count == 0


@pytest.mark.asyncio
async def test_save_events_multiple(db_session):
    """複数件の一括保存。"""
    now = datetime.now(timezone.utc)
    events = [
        EarthquakeEvent(
            event_id=f"batch-{i}", magnitude=4.0 + i * 0.1, depth_km=20.0,
            latitude=35.0, longitude=139.0, region="テスト",
            timestamp=now, source="usgs",
        )
        for i in range(5)
    ]
    count = await save_events(events)
    assert count == 5
```

- [ ] **Step 4.2: テストが失敗することを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_event_store.py -v
```

- [ ] **Step 4.3: event_store.py を実装する**

`backend/app/usecases/event_store.py` を作成:

```python
"""地震イベントの全件保存。magnitude_threshold 以下も含む。"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import EarthquakeEvent
from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import EarthquakeEventDB

logger = logging.getLogger(__name__)


async def save_events(events: list[EarthquakeEvent]) -> int:
    """イベントを earthquake_events に一括保存する。
    event_id が既に存在する場合は無視。
    戻り値: 新規保存した件数。
    """
    if not events:
        return 0

    factory = get_session_factory()
    saved = 0
    async with factory() as session:
        for event in events:
            existing = await session.execute(
                select(EarthquakeEventDB.event_id).where(
                    EarthquakeEventDB.event_id == event.event_id
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(),
                event_id=event.event_id,
                source=event.source,
                magnitude=event.magnitude,
                depth_km=event.depth_km,
                latitude=event.latitude,
                longitude=event.longitude,
                region=event.region,
                occurred_at=event.timestamp,
                fetched_at=datetime.now(timezone.utc),
            ))
            saved += 1
        await session.commit()

    if saved > 0:
        logger.info("[EventStore] %d 件保存（%d 件中）", saved, len(events))
    return saved
```

- [ ] **Step 4.4: テストがパスすることを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_event_store.py -v
```

期待: 4件 PASSED

- [ ] **Step 4.5: コミット**

```bash
git add backend/app/usecases/event_store.py backend/tests/test_event_store.py
git commit -m "feat(usecases): add event_store for bulk earthquake event persistence"
```

---

## Task 5: multi_source.py にイベント保存を統合

**Files:**
- Modify: `backend/app/infrastructure/multi_source.py`

- [ ] **Step 5.1: api.py の _process_event にイベント保存を追加する**

`backend/app/interfaces/api.py` の `_process_event` 関数を変更する。WebSocket モード経由のイベントも earthquake_events に保存されるようにする:

変更前:
```python
async def _process_event(event) -> None:
    initial_state = {
```

変更後:
```python
async def _process_event(event) -> None:
    # earthquake_events に保存（WS モードでも漏れないようここで保存）
    try:
        from app.usecases.event_store import save_events
        await save_events([event])
    except Exception as e:
        logger.warning("[Monitor] イベント保存失敗: %s", e)

    initial_state = {
```

- [ ] **Step 5.2: multi_source.py を変更する**

`backend/app/infrastructure/multi_source.py` の `fetch_all_sources` 関数末尾を変更:

変更前:
```python
    deduped = _deduplicate(all_events)
    logger.info("[MultiSource] 統合 %d 件（重複除去前: %d 件）", len(deduped), len(all_events))
    return deduped
```

変更後:
```python
    deduped = _deduplicate(all_events)
    logger.info("[MultiSource] 統合 %d 件（重複除去前: %d 件）", len(deduped), len(all_events))

    # 全イベントを earthquake_events テーブルに保存
    try:
        from app.usecases.event_store import save_events
        await save_events(deduped)
    except Exception as e:
        logger.error("[MultiSource] イベント保存失敗: %s", e)

    return deduped
```

- [ ] **Step 5.3: 既存テストがパスすることを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_multi_source.py tests/test_api.py -v
```

- [ ] **Step 5.4: コミット**

```bash
git add backend/app/infrastructure/multi_source.py backend/app/interfaces/api.py
git commit -m "feat: save all fetched events to earthquake_events table"
```

---

## Task 6: GET /events エンドポイント

**Files:**
- Modify: `backend/app/infrastructure/db.py`
- Modify: `backend/app/interfaces/api.py`
- Create: `backend/tests/test_events_api.py`

- [ ] **Step 6.1: テストを作成する**

`backend/tests/test_events_api.py` を作成:

```python
"""GET /events エンドポイントのテスト。"""
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone

from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import EarthquakeEventDB


async def _seed_events(count: int = 5):
    """テスト用イベントを挿入する。"""
    factory = get_session_factory()
    async with factory() as session:
        for i in range(count):
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(),
                event_id=f"seed-{i:03d}",
                source="p2p",
                magnitude=3.0 + i * 0.5,
                depth_km=10.0 + i,
                latitude=35.0 + i * 0.1,
                longitude=139.0,
                region="東京都" if i % 2 == 0 else "大阪府",
                occurred_at=datetime(2026, 3, 26, 10, i, 0, tzinfo=timezone.utc),
                fetched_at=datetime.now(timezone.utc),
            ))
        await session.commit()


@pytest.mark.asyncio
async def test_get_events_empty(async_client, db_engine):
    resp = await async_client.get("/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["events"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_events_with_data(async_client, db_engine):
    await _seed_events(5)
    resp = await async_client.get("/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["events"]) == 5


@pytest.mark.asyncio
async def test_get_events_filter_magnitude(async_client, db_engine):
    await _seed_events(5)
    resp = await async_client.get("/events?min_magnitude=4.5")
    assert resp.status_code == 200
    data = resp.json()
    for ev in data["events"]:
        assert ev["magnitude"] >= 4.5


@pytest.mark.asyncio
async def test_get_events_filter_region(async_client, db_engine):
    await _seed_events(5)
    resp = await async_client.get("/events?region=東京都")
    assert resp.status_code == 200
    data = resp.json()
    for ev in data["events"]:
        assert ev["region"] == "東京都"


@pytest.mark.asyncio
async def test_get_events_pagination(async_client, db_engine):
    await _seed_events(5)
    resp = await async_client.get("/events?limit=2&offset=0")
    data = resp.json()
    assert len(data["events"]) == 2
    assert data["total"] == 5
```

- [ ] **Step 6.2: テストが失敗することを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_events_api.py -v
```

- [ ] **Step 6.3: db.py に get_events 関数を追加する**

`backend/app/infrastructure/db.py` の末尾に追記:

```python
async def get_events(
    limit: int = 50,
    offset: int = 0,
    min_magnitude: float | None = None,
    region: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> tuple[list[dict], int]:
    """イベント履歴を検索する。(events, total) を返す。"""
    factory = get_session_factory()
    async with factory() as session:
        query = select(EarthquakeEventDB)
        count_query = select(func.count()).select_from(EarthquakeEventDB)

        if min_magnitude is not None:
            query = query.where(EarthquakeEventDB.magnitude >= min_magnitude)
            count_query = count_query.where(EarthquakeEventDB.magnitude >= min_magnitude)
        if region is not None:
            query = query.where(EarthquakeEventDB.region == region)
            count_query = count_query.where(EarthquakeEventDB.region == region)
        if start is not None:
            query = query.where(EarthquakeEventDB.occurred_at >= start)
            count_query = count_query.where(EarthquakeEventDB.occurred_at >= start)
        if end is not None:
            query = query.where(EarthquakeEventDB.occurred_at <= end)
            count_query = count_query.where(EarthquakeEventDB.occurred_at <= end)

        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(EarthquakeEventDB.occurred_at.desc()).limit(limit).offset(offset)
        result = await session.execute(query)
        rows = result.scalars().all()

    return [
        {
            "event_id": r.event_id,
            "source": r.source,
            "magnitude": r.magnitude,
            "depth_km": r.depth_km,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "region": r.region,
            "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
        }
        for r in rows
    ], total
```

- [ ] **Step 6.4: api.py に GET /events エンドポイントを追加する**

`backend/app/interfaces/api.py` の `get_alerts` エンドポイントの後に追記:

```python
@app.get("/events")
async def get_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    min_magnitude: Optional[float] = None,
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    from datetime import datetime as dt
    start_dt = dt.fromisoformat(start) if start else None
    end_dt = dt.fromisoformat(end) if end else None
    events, total = await db.get_events(
        limit=limit, offset=offset,
        min_magnitude=min_magnitude, region=region,
        start=start_dt, end=end_dt,
    )
    return {"events": events, "total": total, "limit": limit, "offset": offset}
```

- [ ] **Step 6.5: テストがパスすることを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_events_api.py -v
```

期待: 5件 PASSED

- [ ] **Step 6.6: コミット**

```bash
git add backend/app/infrastructure/db.py backend/app/interfaces/api.py backend/tests/test_events_api.py
git commit -m "feat(api): add GET /events endpoint with filtering and pagination"
```

---

## Task 7: GET/PUT /settings エンドポイント

**Files:**
- Modify: `backend/app/infrastructure/db.py`
- Modify: `backend/app/interfaces/api.py`
- Create: `backend/tests/test_settings_api.py`

- [ ] **Step 7.1: テストを作成する**

`backend/tests/test_settings_api.py` を作成:

```python
"""GET/PUT /settings エンドポイントのテスト。"""
import pytest


@pytest.mark.asyncio
async def test_get_settings_default(async_client, db_engine):
    """初回アクセスでデフォルト設定が自動作成される。"""
    resp = await async_client.get("/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["min_severity"] == "LOW"
    assert data["region_filters"] == []
    assert data["notification_channels"] == []


@pytest.mark.asyncio
async def test_put_settings(async_client, db_engine):
    """設定を更新できる。"""
    resp = await async_client.put("/settings", json={
        "min_severity": "HIGH",
        "region_filters": ["東京都", "大阪府"],
        "notification_channels": [{"type": "discord", "url": "https://example.com/webhook"}],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["min_severity"] == "HIGH"
    assert data["region_filters"] == ["東京都", "大阪府"]
    assert len(data["notification_channels"]) == 1


@pytest.mark.asyncio
async def test_put_then_get_settings(async_client, db_engine):
    """PUT した設定が GET で取得できる。"""
    await async_client.put("/settings", json={
        "min_severity": "MEDIUM",
        "region_filters": ["宮城県"],
        "notification_channels": [],
    })
    resp = await async_client.get("/settings")
    data = resp.json()
    assert data["min_severity"] == "MEDIUM"
    assert data["region_filters"] == ["宮城県"]


@pytest.mark.asyncio
async def test_put_settings_invalid_severity(async_client, db_engine):
    """無効な severity は 422。"""
    resp = await async_client.put("/settings", json={
        "min_severity": "INVALID",
    })
    assert resp.status_code == 422
```

- [ ] **Step 7.2: テストが失敗することを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_settings_api.py -v
```

- [ ] **Step 7.3: db.py にユーザー設定関数を追加する**

`backend/app/infrastructure/db.py` の末尾に追記:

```python
async def get_user_settings(user_id: str = "default") -> dict:
    """ユーザー設定を取得する。存在しなければデフォルトで自動作成。"""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(UserSettingsDB).where(UserSettingsDB.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            now = datetime.now(timezone.utc)
            row = UserSettingsDB(
                id=uuid.uuid4(), user_id=user_id,
                min_severity="LOW", region_filters=[], notification_channels=[],
                created_at=now, updated_at=now,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return {
            "min_severity": row.min_severity,
            "region_filters": row.region_filters or [],
            "notification_channels": row.notification_channels or [],
        }


async def update_user_settings(
    user_id: str = "default",
    min_severity: str | None = None,
    region_filters: list | None = None,
    notification_channels: list | None = None,
) -> dict:
    """ユーザー設定を更新する。"""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(UserSettingsDB).where(UserSettingsDB.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if row is None:
            row = UserSettingsDB(
                id=uuid.uuid4(), user_id=user_id,
                min_severity=min_severity or "LOW",
                region_filters=region_filters or [],
                notification_channels=notification_channels or [],
                created_at=now, updated_at=now,
            )
            session.add(row)
        else:
            if min_severity is not None:
                row.min_severity = min_severity
            if region_filters is not None:
                row.region_filters = region_filters
            if notification_channels is not None:
                row.notification_channels = notification_channels
            row.updated_at = now
        await session.commit()
        await session.refresh(row)
    return {
        "min_severity": row.min_severity,
        "region_filters": row.region_filters or [],
        "notification_channels": row.notification_channels or [],
    }
```

- [ ] **Step 7.4: api.py に GET/PUT /settings を追加する**

`backend/app/interfaces/api.py` に追記:

```python
from pydantic import BaseModel, field_validator
from typing import Literal

# 既存のimportセクションに追加（ファイル上部）


class SettingsUpdate(BaseModel):
    min_severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    region_filters: list[str] | None = None
    notification_channels: list[dict] | None = None

    @field_validator("min_severity", mode="before")
    @classmethod
    def validate_severity(cls, v):
        if v is not None and v not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            raise ValueError("severity は LOW/MEDIUM/HIGH/CRITICAL のいずれかです")
        return v


@app.get("/settings")
async def get_settings():
    return await db.get_user_settings()


@app.put("/settings")
async def update_settings(body: SettingsUpdate):
    return await db.update_user_settings(
        min_severity=body.min_severity,
        region_filters=body.region_filters,
        notification_channels=body.notification_channels,
    )
```

- [ ] **Step 7.5: テストがパスすることを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_settings_api.py -v
```

期待: 4件 PASSED

- [ ] **Step 7.6: コミット**

```bash
git add backend/app/infrastructure/db.py backend/app/interfaces/api.py backend/tests/test_settings_api.py
git commit -m "feat(api): add GET/PUT /settings for user notification preferences"
```

---

## Task 8: Alembic セットアップ + docker-compose 更新 + 全体テスト

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/001_initial.py`
- Modify: `docker-compose.yml`

- [ ] **Step 8.1: alembic.ini を作成する**

`backend/alembic.ini` を作成:

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://quakemind:quakemind_dev@localhost:5432/quakemind

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 8.2: alembic/env.py を作成する**

`backend/alembic/env.py` を作成:

```python
"""Alembic async 環境設定。"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

from app.infrastructure.models_db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 8.3: alembic/script.py.mako を作成する**

`backend/alembic/script.py.mako` を作成:

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 8.4: 初期マイグレーションファイルを作成する**

`backend/alembic/versions/001_initial_tables.py` を作成:

```python
"""Initial tables: earthquake_events, alerts, seen_events, user_settings.

Revision ID: 001
Revises:
Create Date: 2026-03-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "earthquake_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_id", sa.String(), unique=True, nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("magnitude", sa.Float(), nullable=False),
        sa.Column("depth_km", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("region", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_events_occurred_at", "earthquake_events", ["occurred_at"])
    op.create_index("ix_events_region", "earthquake_events", ["region"])
    op.create_index("ix_events_magnitude", "earthquake_events", ["magnitude"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_id", sa.String(), sa.ForeignKey("earthquake_events.event_id"), unique=True, nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("ja_text", sa.Text(), nullable=False),
        sa.Column("en_text", sa.Text(), nullable=False),
        sa.Column("is_fallback", sa.Boolean(), default=False),
        sa.Column("risk_json", sa.JSON(), nullable=True),
        sa.Column("route_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])
    op.create_index("ix_alerts_severity", "alerts", ["severity"])

    op.create_table(
        "seen_events",
        sa.Column("event_id", sa.String(), primary_key=True),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "user_settings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.String(), unique=True, nullable=False),
        sa.Column("min_severity", sa.String(), default="LOW"),
        sa.Column("region_filters", sa.JSON(), default=list),
        sa.Column("notification_channels", sa.JSON(), default=list),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
    op.drop_table("seen_events")
    op.drop_table("alerts")
    op.drop_table("earthquake_events")
```

- [ ] **Step 8.5: docker-compose.yml を更新する**

`docker-compose.yml` の backend service に DATABASE_URL を追加し、backend_data ボリュームを削除:

変更点:
- `backend.environment` に `DATABASE_URL=postgresql+asyncpg://quakemind:quakemind_dev@db:5432/quakemind` を追加
- `backend.volumes` の `backend_data:/app/data` を削除
- `volumes` から `backend_data:` を削除

- [ ] **Step 8.6: .env.example を更新する**

`backend/.env.example` に追記:

```
# データベース
DATABASE_URL=postgresql+asyncpg://quakemind:quakemind_dev@localhost:5432/quakemind
```

- [ ] **Step 8.7: 全テストを実行する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/ -v --ignore=tests/test_poseidon_loader.py
```

期待: 全件 PASSED

- [ ] **Step 8.8: コミット**

```bash
git add backend/alembic.ini backend/alembic/ docker-compose.yml backend/.env.example
git commit -m "feat(infra): add Alembic migrations, update docker-compose for PostgreSQL"
```

---

## 完了条件

- [ ] SQLAlchemy モデル4つが定義されている
- [ ] db.py が SQLAlchemy async session で動作する
- [ ] event_store.save_events() で全イベントが保存される
- [ ] GET /events でフィルタ付き検索ができる
- [ ] GET/PUT /settings でユーザー設定の取得・更新ができる
- [ ] Alembic マイグレーションが定義されている
- [ ] docker-compose.yml が PostgreSQL に対応している
- [ ] 全テスト PASSED
