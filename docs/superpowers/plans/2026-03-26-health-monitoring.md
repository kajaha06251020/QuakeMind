# Phase C #13: ヘルスモニタリング強化 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GET /health エンドポイントを追加し、DB・LLMサーバー・データソースの死活状態とアップタイムを一括確認できるようにする。

**Architecture:** `health.py` がDB ping・LLM ping・データソースステータス収集を担当。`multi_source.py` が fetch 結果をモジュール変数に記録。`api.py` に GET /health を追加。

**Tech Stack:** Python 3.12+, FastAPI, httpx, SQLAlchemy async, pytest-asyncio, pytest-httpx

**Spec:** `docs/superpowers/specs/2026-03-26-health-monitoring-design.md`

---

## ファイル構成

```
backend/
├── app/
│   ├── services/
│   │   └── health.py                # (新規) ヘルスチェックロジック
│   ├── infrastructure/
│   │   └── multi_source.py          # (変更) ソースステータス記録追加
│   └── interfaces/
│       └── api.py                   # (変更) GET /health + started_at 記録
└── tests/
    └── test_health.py               # (新規)
```

---

## Task 1: multi_source.py にソースステータス記録を追加

**Files:**
- Modify: `backend/app/infrastructure/multi_source.py`

- [ ] **Step 1.1: ステータス記録用のモジュール変数と関数を追加する**

`backend/app/infrastructure/multi_source.py` の `logger` 定義の後（`_LAT_THRESHOLD` の前）に追加:

```python
from datetime import datetime, timezone

# データソースの最終取得ステータス
_source_status: dict[str, dict] = {}


def get_source_status() -> dict[str, dict]:
    """各データソースの最終取得ステータスを返す。"""
    return _source_status.copy()
```

既存の `from datetime import timezone` を `from datetime import datetime, timezone` に変更する。

- [ ] **Step 1.2: fetch_all_sources 内でステータスを記録する**

`fetch_all_sources` の for ループを変更する。

変更前:
```python
    for name, result in zip(source_names, results):
        if isinstance(result, Exception):
            logger.error("[MultiSource] %s エラー: %s", name, result)
        else:
            all_events.extend(result)
            logger.debug("[MultiSource] %s: %d 件", name, len(result))
```

変更後:
```python
    now = datetime.now(timezone.utc)
    for name, result in zip(source_names, results):
        if isinstance(result, Exception):
            logger.error("[MultiSource] %s エラー: %s", name, result)
            _source_status[name] = {
                "last_fetch_at": now.isoformat(),
                "last_error": str(result),
            }
        else:
            all_events.extend(result)
            logger.debug("[MultiSource] %s: %d 件", name, len(result))
            _source_status[name] = {
                "last_fetch_at": now.isoformat(),
                "last_error": None,
            }
```

- [ ] **Step 1.3: 既存テストがパスすることを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_multi_source.py -v
```

- [ ] **Step 1.4: コミット**

```bash
git add backend/app/infrastructure/multi_source.py
git commit -m "feat(multi_source): record per-source fetch status for health monitoring"
```

---

## Task 2: health.py ヘルスチェックロジック

**Files:**
- Create: `backend/app/services/health.py`
- Create: `backend/tests/test_health.py`

- [ ] **Step 2.1: テストを作成する**

`backend/tests/test_health.py` を作成:

```python
"""ヘルスチェックのテスト。"""
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

from app.services.health import check_health


@pytest.mark.asyncio
async def test_health_all_healthy(db_engine, httpx_mock):
    """全コンポーネント正常時は healthy。"""
    httpx_mock.add_response(url="http://127.0.0.1:8081/health", status_code=200)

    with patch("app.services.health.get_source_status", return_value={
        "p2p": {"last_fetch_at": "2026-03-26T10:00:00+00:00", "last_error": None},
        "usgs": {"last_fetch_at": "2026-03-26T10:00:00+00:00", "last_error": None},
    }):
        result = await check_health()

    assert result["status"] == "healthy"
    assert result["components"]["database"]["status"] == "healthy"
    assert result["components"]["llm_server"]["status"] == "healthy"
    assert result["components"]["data_sources"]["p2p"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_llm_down(db_engine, httpx_mock):
    """LLMサーバー未起動時は degraded。"""
    import httpx
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

    with patch("app.services.health.get_source_status", return_value={}):
        result = await check_health()

    assert result["status"] == "degraded"
    assert result["components"]["llm_server"]["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_health_source_has_error(db_engine, httpx_mock):
    """データソースにエラーがある場合。"""
    httpx_mock.add_response(url="http://127.0.0.1:8081/health", status_code=200)

    with patch("app.services.health.get_source_status", return_value={
        "p2p": {"last_fetch_at": "2026-03-26T10:00:00+00:00", "last_error": "timeout"},
    }):
        result = await check_health()

    assert result["components"]["data_sources"]["p2p"]["status"] == "unhealthy"
    assert result["components"]["data_sources"]["p2p"]["last_error"] == "timeout"
    assert result["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_claude_provider(db_engine):
    """llm_provider=claude の場合、LLMサーバーチェックをスキップ。"""
    with (
        patch("app.services.health.settings") as mock_settings,
        patch("app.services.health.get_source_status", return_value={}),
    ):
        mock_settings.llm_provider = "claude"
        mock_settings.local_llm_base_url = "http://127.0.0.1:8081"
        mock_settings.database_url = "sqlite+aiosqlite://"
        result = await check_health()

    assert result["components"]["llm_server"]["status"] == "skipped"
    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_uptime(db_engine, httpx_mock):
    """uptime_seconds と started_at が含まれる。"""
    httpx_mock.add_response(url="http://127.0.0.1:8081/health", status_code=200)

    with patch("app.services.health.get_source_status", return_value={}):
        result = await check_health()

    assert "uptime_seconds" in result
    assert "started_at" in result
    assert result["uptime_seconds"] >= 0
```

- [ ] **Step 2.2: テストが失敗することを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_health.py -v
```

期待: FAILED（`health` モジュールが存在しない）

- [ ] **Step 2.3: health.py を実装する**

`backend/app/services/health.py` を作成:

```python
"""ヘルスチェックロジック。"""
import time
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import text

from app.config import settings
from app.infrastructure.database import get_session_factory
from app.infrastructure.multi_source import get_source_status

logger = logging.getLogger(__name__)

_started_at: datetime = datetime.now(timezone.utc)
_start_time: float = time.monotonic()


def set_started_at() -> None:
    """アプリ起動時に呼ぶ。"""
    global _started_at, _start_time
    _started_at = datetime.now(timezone.utc)
    _start_time = time.monotonic()


async def _check_database() -> dict:
    """DB 接続チェック。"""
    try:
        factory = get_session_factory()
        start = time.monotonic()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        latency = round((time.monotonic() - start) * 1000, 1)
        return {"status": "healthy", "latency_ms": latency}
    except Exception as e:
        logger.warning("[Health] DB チェック失敗: %s", e)
        return {"status": "unhealthy", "error": str(e)}


async def _check_llm_server() -> dict:
    """LLM サーバーチェック。"""
    if settings.llm_provider != "local":
        return {"status": "skipped", "provider": settings.llm_provider}
    try:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.local_llm_base_url}/health")
            resp.raise_for_status()
        latency = round((time.monotonic() - start) * 1000, 1)
        return {
            "status": "healthy",
            "provider": "local",
            "base_url": settings.local_llm_base_url,
            "latency_ms": latency,
        }
    except Exception as e:
        logger.warning("[Health] LLM チェック失敗: %s", e)
        return {
            "status": "unhealthy",
            "provider": "local",
            "base_url": settings.local_llm_base_url,
            "error": str(e),
        }


def _check_data_sources() -> dict:
    """データソースの最終取得ステータスを整形して返す。"""
    raw = get_source_status()
    # 既知のソース一覧
    known_sources = {
        "p2p": True,
        "usgs": settings.usgs_enabled,
        "jma_xml": settings.jma_xml_enabled,
    }
    result = {}
    for name, enabled in known_sources.items():
        if not enabled and name not in raw:
            result[name] = {"status": "disabled", "last_fetch_at": None, "last_error": None}
        elif name in raw:
            entry = raw[name]
            status = "healthy" if entry.get("last_error") is None else "unhealthy"
            result[name] = {
                "status": status,
                "last_fetch_at": entry.get("last_fetch_at"),
                "last_error": entry.get("last_error"),
            }
        else:
            result[name] = {"status": "unknown", "last_fetch_at": None, "last_error": None}
    return result


async def check_health() -> dict:
    """全コンポーネントのヘルスチェックを実行する。"""
    db_status = await _check_database()
    llm_status = await _check_llm_server()
    source_status = _check_data_sources()

    # 全体ステータス判定
    all_statuses = [db_status["status"]]
    if llm_status["status"] not in ("skipped",):
        all_statuses.append(llm_status["status"])
    all_statuses.extend(
        s["status"] for s in source_status.values()
        if s["status"] not in ("disabled", "unknown")
    )
    overall = "healthy" if all(s == "healthy" for s in all_statuses) else "degraded"

    return {
        "status": overall,
        "uptime_seconds": round(time.monotonic() - _start_time, 1),
        "started_at": _started_at.isoformat(),
        "components": {
            "database": db_status,
            "llm_server": llm_status,
            "data_sources": source_status,
        },
    }
```

- [ ] **Step 2.4: テストがパスすることを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_health.py -v
```

期待: 5件 PASSED

- [ ] **Step 2.5: コミット**

```bash
git add backend/app/services/health.py backend/tests/test_health.py
git commit -m "feat(services): add health check logic for DB, LLM, and data sources"
```

---

## Task 3: GET /health エンドポイント + lifespan 更新

**Files:**
- Modify: `backend/app/interfaces/api.py`

- [ ] **Step 3.1: api.py に GET /health を追加し、lifespan で started_at を記録する**

`backend/app/interfaces/api.py` の lifespan 関数内、`await db.init_db()` の直後（`if settings.p2p_ws_url:` の前）に追加:

```python
    from app.services.health import set_started_at
    set_started_at()
```

ファイル末尾（最後のエンドポイントの後）に追加:

```python
@app.get("/health")
async def health_check():
    from app.services.health import check_health
    return await check_health()
```

- [ ] **Step 3.2: 全テストがパスすることを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/ -v --ignore=tests/test_poseidon_loader.py
```

期待: 全件 PASSED

- [ ] **Step 3.3: コミット**

```bash
git add backend/app/interfaces/api.py
git commit -m "feat(api): add GET /health endpoint with component status"
```

---

## 完了条件

- [ ] GET /health が全コンポーネントの状態を返す
- [ ] DB接続チェックが動作する
- [ ] LLMサーバーチェックが動作する（provider=claude ならスキップ）
- [ ] データソースの最終取得ステータスが表示される
- [ ] 全テスト PASSED
