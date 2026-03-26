# Phase C1: 統計分析基盤 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** earthquake_events テーブルのデータを既存の seismic_analysis.py に接続し、GET ベースの統計分析 API 5本を公開する。フラクタル次元解析と b値時系列追跡を新規追加する。

**Architecture:** `db.py` に `get_events_as_records()` を追加して earthquake_events → EarthquakeRecord 変換を行い、`statistics_router.py` が GET パラメータで絞り込んだデータを既存/新規の解析関数に渡して結果を返す。既存の POST ベースの analysis_router はそのまま維持。

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy async, numpy, scipy, pytest-asyncio

**Spec:** `docs/superpowers/specs/2026-03-26-phase-c1-statistical-analysis-design.md`

---

## ファイル構成

```
backend/
├── app/
│   ├── infrastructure/
│   │   └── db.py                         # (変更) get_events_as_records() 追加
│   ├── usecases/
│   │   ├── seismic_analysis.py           # (既存, 変更なし)
│   │   ├── fractal.py                    # (新規) フラクタル次元解析
│   │   └── b_value_tracker.py            # (新規) b値/a値 時系列追跡
│   └── interfaces/
│       ├── api.py                        # (変更) statistics_router を include
│       ├── analysis_router.py            # (既存, 変更なし)
│       └── statistics_router.py          # (新規) GET ベース統計分析 API
├── tests/
│   ├── test_fractal.py                   # (新規)
│   ├── test_b_value_tracker.py           # (新規)
│   └── test_statistics_api.py            # (新規)
```

---

## Task 1: db.py に get_events_as_records() を追加

**Files:**
- Modify: `backend/app/infrastructure/db.py`

earthquake_events テーブルから EarthquakeRecord（seismic_analysis.py が要求する形式）のリストを返す関数。

- [ ] **Step 1.1: 関数を db.py の末尾に追加する**

```python
async def get_events_as_records(
    region: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    min_magnitude: float | None = None,
) -> list:
    """earthquake_events から EarthquakeRecord 形式のリストを返す。"""
    from app.domain.seismology import EarthquakeRecord

    factory = get_session_factory()
    async with factory() as session:
        query = select(EarthquakeEventDB)
        if region is not None:
            query = query.where(EarthquakeEventDB.region == region)
        if start is not None:
            query = query.where(EarthquakeEventDB.occurred_at >= start)
        if end is not None:
            query = query.where(EarthquakeEventDB.occurred_at <= end)
        if min_magnitude is not None:
            query = query.where(EarthquakeEventDB.magnitude >= min_magnitude)
        query = query.order_by(EarthquakeEventDB.occurred_at.asc())
        result = await session.execute(query)
        rows = result.scalars().all()

    return [
        EarthquakeRecord(
            event_id=r.event_id,
            magnitude=r.magnitude,
            latitude=r.latitude,
            longitude=r.longitude,
            depth_km=r.depth_km,
            timestamp=r.occurred_at.isoformat() if r.occurred_at else "",
        )
        for r in rows
    ]
```

- [ ] **Step 1.2: コミット**

```bash
git add backend/app/infrastructure/db.py
git commit -m "feat(db): add get_events_as_records for seismic analysis"
```

---

## Task 2: フラクタル次元解析（fractal.py）

**Files:**
- Create: `backend/app/usecases/fractal.py`
- Create: `backend/tests/test_fractal.py`

- [ ] **Step 2.1: テストを作成する**

`backend/tests/test_fractal.py`:

```python
"""フラクタル次元解析のテスト。"""
import pytest
import numpy as np
from app.usecases.fractal import compute_correlation_dimension


def test_clustered_points_low_d():
    """集中した点群は D2 が低い。"""
    rng = np.random.default_rng(42)
    # 1点の周囲にガウス分布で集中
    lats = 35.0 + rng.normal(0, 0.01, 100)
    lons = 139.0 + rng.normal(0, 0.01, 100)
    d2 = compute_correlation_dimension(lats, lons)
    assert d2 is not None
    assert 0.0 < d2 < 2.0


def test_scattered_points_high_d():
    """広く散らばった点群は D2 が高い。"""
    rng = np.random.default_rng(42)
    lats = 30.0 + rng.uniform(0, 10, 200)
    lons = 130.0 + rng.uniform(0, 10, 200)
    d2 = compute_correlation_dimension(lats, lons)
    assert d2 is not None
    assert d2 > 1.0


def test_too_few_points():
    """点が少なすぎる場合は None。"""
    d2 = compute_correlation_dimension(
        np.array([35.0, 35.1]),
        np.array([139.0, 139.1]),
    )
    assert d2 is None


def test_identical_points():
    """全て同じ点の場合は D2 ≈ 0。"""
    lats = np.full(50, 35.0)
    lons = np.full(50, 139.0)
    d2 = compute_correlation_dimension(lats, lons)
    assert d2 is not None
    assert d2 < 0.5
```

- [ ] **Step 2.2: テストが失敗することを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_fractal.py -v
```

- [ ] **Step 2.3: fractal.py を実装する**

`backend/app/usecases/fractal.py`:

```python
"""フラクタル次元解析（相関次元 D2）。"""
import math
import logging

import numpy as np

logger = logging.getLogger(__name__)

_MIN_EVENTS = 10


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


def compute_correlation_dimension(
    latitudes: np.ndarray,
    longitudes: np.ndarray,
) -> float | None:
    """
    相関次元 D2 を計算する。

    C(r) = (2 / N(N-1)) * Σ H(r - dist(i,j))
    D2 = 傾き of log(C(r)) vs log(r)

    Returns None if insufficient data.
    """
    n = len(latitudes)
    if n < _MIN_EVENTS:
        return None

    # 全ペアの距離を計算
    distances = []
    for i in range(n):
        for j in range(i + 1, n):
            d = _haversine_km(latitudes[i], longitudes[i], latitudes[j], longitudes[j])
            if d > 0:
                distances.append(d)

    if len(distances) < 10:
        return 0.0

    distances = np.array(distances)
    d_min = max(distances.min(), 0.01)
    d_max = distances.max()

    if d_min >= d_max:
        return 0.0

    # 対数等間隔の半径ビン
    r_values = np.logspace(np.log10(d_min), np.log10(d_max), 20)
    n_pairs = n * (n - 1) / 2

    log_r = []
    log_c = []
    for r in r_values:
        count = np.sum(distances <= r)
        c_r = count / n_pairs
        if c_r > 0:
            log_r.append(np.log10(r))
            log_c.append(np.log10(c_r))

    if len(log_r) < 5:
        return 0.0

    # 線形回帰で傾きを推定
    log_r = np.array(log_r)
    log_c = np.array(log_c)
    # 中央部分（スケーリング領域）を使用
    n_pts = len(log_r)
    start = n_pts // 4
    end = 3 * n_pts // 4
    if end - start < 3:
        start, end = 0, n_pts

    x = log_r[start:end]
    y = log_c[start:end]

    if len(x) < 2:
        return 0.0

    coeffs = np.polyfit(x, y, 1)
    d2 = float(coeffs[0])
    return round(max(0.0, d2), 2)
```

- [ ] **Step 2.4: テストがパスすることを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_fractal.py -v
```

期待: 4件 PASSED

- [ ] **Step 2.5: コミット**

```bash
git add backend/app/usecases/fractal.py backend/tests/test_fractal.py
git commit -m "feat(usecases): add correlation dimension (D2) fractal analysis"
```

---

## Task 3: b値時系列追跡（b_value_tracker.py）

**Files:**
- Create: `backend/app/usecases/b_value_tracker.py`
- Create: `backend/tests/test_b_value_tracker.py`

- [ ] **Step 3.1: テストを作成する**

`backend/tests/test_b_value_tracker.py`:

```python
"""b値時系列追跡のテスト。"""
import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.b_value_tracker import compute_b_value_timeseries


def _make_events(n: int, start_date: datetime, days_span: int = 180) -> list[EarthquakeRecord]:
    """テスト用イベントを生成。"""
    import random
    random.seed(42)
    events = []
    for i in range(n):
        t = start_date + timedelta(days=random.uniform(0, days_span))
        events.append(EarthquakeRecord(
            event_id=f"test-{i:04d}",
            magnitude=round(random.uniform(1.5, 6.0), 1),
            latitude=35.0 + random.uniform(-1, 1),
            longitude=139.0 + random.uniform(-1, 1),
            depth_km=random.uniform(5, 100),
            timestamp=t.isoformat(),
        ))
    return events


def test_timeseries_basic():
    """基本的な時系列が返ること。"""
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = _make_events(100, start)
    result = compute_b_value_timeseries(events, window_days=90, step_days=30)
    assert len(result) > 0
    for entry in result:
        assert "start" in entry
        assert "end" in entry
        assert "b_value" in entry
        assert "a_value" in entry
        assert "n_events" in entry


def test_timeseries_insufficient_data():
    """イベントが少なすぎる場合は空リスト。"""
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = _make_events(3, start, days_span=10)
    result = compute_b_value_timeseries(events, window_days=90, step_days=30)
    assert result == []


def test_timeseries_window_size():
    """ウィンドウサイズが結果に影響すること。"""
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = _make_events(200, start, days_span=365)
    result_90 = compute_b_value_timeseries(events, window_days=90, step_days=30)
    result_180 = compute_b_value_timeseries(events, window_days=180, step_days=30)
    # 大きいウィンドウ → 少ないポイント
    assert len(result_90) >= len(result_180)
```

- [ ] **Step 3.2: テストが失敗することを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_b_value_tracker.py -v
```

- [ ] **Step 3.3: b_value_tracker.py を実装する**

`backend/app/usecases/b_value_tracker.py`:

```python
"""b値/a値の時系列追跡。スライディングウィンドウで計算。"""
import logging
from datetime import datetime, timedelta, timezone

from app.domain.seismology import EarthquakeRecord
from app.usecases.seismic_analysis import analyze_gutenberg_richter

logger = logging.getLogger(__name__)

_MIN_EVENTS_PER_WINDOW = 10


def compute_b_value_timeseries(
    events: list[EarthquakeRecord],
    window_days: int = 90,
    step_days: int = 30,
) -> list[dict]:
    """
    スライディングウィンドウで b値/a値 の時系列を計算する。

    Args:
        events: 時刻順ソート済みの EarthquakeRecord リスト
        window_days: ウィンドウ幅（日）
        step_days: ステップ幅（日）

    Returns:
        [{"start": ISO, "end": ISO, "b_value": float, "a_value": float, "n_events": int}, ...]
    """
    if len(events) < _MIN_EVENTS_PER_WINDOW:
        return []

    # タイムスタンプでソート
    def _parse_ts(e: EarthquakeRecord) -> datetime:
        try:
            return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
        except Exception:
            return datetime(2000, 1, 1, tzinfo=timezone.utc)

    sorted_events = sorted(events, key=_parse_ts)
    timestamps = [_parse_ts(e) for e in sorted_events]

    first_time = timestamps[0]
    last_time = timestamps[-1]

    window_delta = timedelta(days=window_days)
    step_delta = timedelta(days=step_days)

    results = []
    current_start = first_time

    while current_start + window_delta <= last_time:
        current_end = current_start + window_delta

        window_events = [
            e for e, t in zip(sorted_events, timestamps)
            if current_start <= t < current_end
        ]

        if len(window_events) >= _MIN_EVENTS_PER_WINDOW:
            try:
                gr = analyze_gutenberg_richter(window_events)
                results.append({
                    "start": current_start.date().isoformat(),
                    "end": current_end.date().isoformat(),
                    "b_value": gr.b_value,
                    "b_uncertainty": gr.b_uncertainty,
                    "a_value": gr.a_value,
                    "mc": gr.mc,
                    "n_events": gr.n_events,
                })
            except (ValueError, Exception) as e:
                logger.debug("[BValueTracker] ウィンドウ %s-%s スキップ: %s",
                            current_start.date(), current_end.date(), e)

        current_start += step_delta

    return results
```

- [ ] **Step 3.4: テストがパスすることを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_b_value_tracker.py -v
```

期待: 3件 PASSED

- [ ] **Step 3.5: コミット**

```bash
git add backend/app/usecases/b_value_tracker.py backend/tests/test_b_value_tracker.py
git commit -m "feat(usecases): add b-value/a-value sliding window time series tracker"
```

---

## Task 4: statistics_router.py（5エンドポイント）

**Files:**
- Create: `backend/app/interfaces/statistics_router.py`
- Create: `backend/tests/test_statistics_api.py`
- Modify: `backend/app/interfaces/api.py`

- [ ] **Step 4.1: テストを作成する**

`backend/tests/test_statistics_api.py`:

```python
"""統計分析 API エンドポイントのテスト。"""
import uuid
import pytest
from datetime import datetime, timezone, timedelta
import random

from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import EarthquakeEventDB


async def _seed_analysis_events(count: int = 50):
    """統計分析用のテストイベントを挿入する。"""
    random.seed(42)
    factory = get_session_factory()
    async with factory() as session:
        base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(count):
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(),
                event_id=f"stat-{uuid.uuid4().hex[:8]}",
                source="p2p",
                magnitude=round(random.uniform(1.5, 6.5), 1),
                depth_km=round(random.uniform(5, 100), 1),
                latitude=35.0 + random.uniform(-2, 2),
                longitude=139.0 + random.uniform(-2, 2),
                region="東京都" if i % 3 != 0 else "大阪府",
                occurred_at=base_time + timedelta(days=random.uniform(0, 180)),
                fetched_at=datetime.now(timezone.utc),
            ))
        await session.commit()


@pytest.mark.asyncio
async def test_get_statistics(async_client, db_engine):
    await _seed_analysis_events(50)
    resp = await async_client.get("/statistics/summary?region=東京都")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_events" in data
    assert "magnitude_distribution" in data
    assert "depth_distribution" in data
    assert data["total_events"] > 0


@pytest.mark.asyncio
async def test_get_statistics_empty(async_client, db_engine):
    resp = await async_client.get("/statistics/summary?region=存在しない")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_events"] == 0


@pytest.mark.asyncio
async def test_get_gutenberg_richter(async_client, db_engine):
    await _seed_analysis_events(100)
    resp = await async_client.get("/statistics/gutenberg-richter")
    assert resp.status_code == 200
    data = resp.json()
    assert "b_value" in data
    assert "a_value" in data
    assert "mc" in data


@pytest.mark.asyncio
async def test_get_b_value_timeseries(async_client, db_engine):
    await _seed_analysis_events(100)
    resp = await async_client.get("/statistics/b-value-timeseries?window_days=60&step_days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert "timeseries" in data
    assert isinstance(data["timeseries"], list)


@pytest.mark.asyncio
async def test_get_fractal_dimension(async_client, db_engine):
    await _seed_analysis_events(50)
    resp = await async_client.get("/statistics/fractal-dimension")
    assert resp.status_code == 200
    data = resp.json()
    assert "d2" in data


@pytest.mark.asyncio
async def test_get_decluster(async_client, db_engine):
    await _seed_analysis_events(50)
    resp = await async_client.get("/statistics/decluster")
    assert resp.status_code == 200
    data = resp.json()
    assert "n_total" in data
    assert "n_mainshocks" in data
    assert "n_aftershocks" in data
```

- [ ] **Step 4.2: テストが失敗することを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_statistics_api.py -v
```

- [ ] **Step 4.3: statistics_router.py を作成する**

`backend/app/interfaces/statistics_router.py`:

```python
"""
統計分析 API ルーター (Phase C1)

GET ベースのエンドポイント。earthquake_events テーブルのデータを使用。
既存の POST ベース /analysis/* はそのまま維持。
"""
import logging
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Query

from app.infrastructure import db
from app.usecases.seismic_analysis import (
    analyze_gutenberg_richter,
    decluster_gardner_knopoff,
)
from app.usecases.fractal import compute_correlation_dimension
from app.usecases.b_value_tracker import compute_b_value_timeseries

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/statistics", tags=["statistics"])


async def _get_records(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    min_magnitude: Optional[float] = None,
):
    """共通: DBからEarthquakeRecordリストを取得する。"""
    from datetime import datetime as dt
    start_dt = dt.fromisoformat(start) if start else None
    end_dt = dt.fromisoformat(end) if end else None
    records = await db.get_events_as_records(
        region=region, start=start_dt, end=end_dt, min_magnitude=min_magnitude,
    )
    return records


@router.get("/summary")
async def get_statistics(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    """地域別統計サマリ。"""
    records = await _get_records(region=region, start=start, end=end)
    if not records:
        return {
            "region": region,
            "total_events": 0,
            "magnitude_distribution": None,
            "depth_distribution": None,
            "frequency_by_magnitude_bin": {},
        }

    mags = np.array([r.magnitude for r in records])
    depths = np.array([r.depth_km for r in records])

    # マグニチュードビン別頻度
    bins = np.arange(np.floor(mags.min()), np.ceil(mags.max()) + 1, 1.0)
    freq_by_bin = {}
    for b in bins:
        count = int(np.sum((mags >= b) & (mags < b + 1)))
        if count > 0:
            freq_by_bin[str(float(b))] = count

    return {
        "region": region,
        "total_events": len(records),
        "magnitude_distribution": {
            "min": round(float(mags.min()), 1),
            "max": round(float(mags.max()), 1),
            "mean": round(float(mags.mean()), 2),
            "median": round(float(np.median(mags)), 2),
        },
        "depth_distribution": {
            "min": round(float(depths.min()), 1),
            "max": round(float(depths.max()), 1),
            "mean": round(float(depths.mean()), 2),
            "median": round(float(np.median(depths)), 2),
        },
        "frequency_by_magnitude_bin": freq_by_bin,
    }


@router.get("/gutenberg-richter")
async def get_gutenberg_richter(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    mc_method: str = Query(default="MBS-WW"),
):
    """Gutenberg-Richter b値/a値解析。"""
    records = await _get_records(region=region, start=start, end=end)
    if len(records) < 10:
        raise HTTPException(status_code=400, detail=f"イベント数が不足しています (n={len(records)}, 最低10必要)")
    try:
        result = analyze_gutenberg_richter(records, mc_method=mc_method)
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/b-value-timeseries")
async def get_b_value_timeseries(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    window_days: int = Query(default=90, ge=30, le=365),
    step_days: int = Query(default=30, ge=7, le=180),
):
    """b値/a値のスライディングウィンドウ時系列。"""
    records = await _get_records(region=region, start=start, end=end)
    timeseries = compute_b_value_timeseries(records, window_days=window_days, step_days=step_days)
    return {
        "region": region,
        "window_days": window_days,
        "step_days": step_days,
        "timeseries": timeseries,
    }


@router.get("/fractal-dimension")
async def get_fractal_dimension(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    """フラクタル次元（相関次元 D2）。"""
    records = await _get_records(region=region, start=start, end=end)
    if len(records) < 10:
        raise HTTPException(status_code=400, detail=f"イベント数が不足しています (n={len(records)}, 最低10必要)")

    lats = np.array([r.latitude for r in records])
    lons = np.array([r.longitude for r in records])
    d2 = compute_correlation_dimension(lats, lons)

    interpretation = ""
    if d2 is not None:
        if d2 < 1.5:
            interpretation = "空間的に強く集中（応力集中の可能性）"
        elif d2 < 2.0:
            interpretation = "やや集中的な分布"
        else:
            interpretation = "広く分散した分布"

    return {
        "region": region,
        "d2": d2,
        "n_events": len(records),
        "interpretation": interpretation,
    }


@router.get("/decluster")
async def get_decluster(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    """Gardner-Knopoff デクラスタリング。"""
    records = await _get_records(region=region, start=start, end=end)
    if len(records) < 2:
        raise HTTPException(status_code=400, detail=f"イベント数が不足しています (n={len(records)}, 最低2必要)")

    result = decluster_gardner_knopoff(records)
    return {
        "method": result.method,
        "n_total": result.n_total,
        "n_mainshocks": result.n_mainshocks,
        "n_aftershocks": result.n_aftershocks,
        "aftershock_ratio": round(result.aftershock_ratio, 4),
    }
```

- [ ] **Step 4.4: api.py に statistics_router を include する**

`backend/app/interfaces/api.py` の `app.include_router(analysis_router)` の後に追加:

```python
from app.interfaces.statistics_router import router as statistics_router
app.include_router(statistics_router)
```

- [ ] **Step 4.5: テストがパスすることを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_statistics_api.py -v
```

期待: 6件 PASSED

- [ ] **Step 4.6: 全テストがパスすることを確認する**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/ -v --ignore=tests/test_poseidon_loader.py
```

- [ ] **Step 4.7: コミット**

```bash
git add backend/app/interfaces/statistics_router.py backend/app/interfaces/api.py backend/tests/test_statistics_api.py
git commit -m "feat(api): add GET-based statistics analysis endpoints (C1)"
```

---

## 完了条件

- [ ] GET /statistics/summary — 地域別統計サマリ
- [ ] GET /statistics/gutenberg-richter — GR解析（b値/a値/Mc）
- [ ] GET /statistics/b-value-timeseries — b値時系列追跡
- [ ] GET /statistics/fractal-dimension — フラクタル次元
- [ ] GET /statistics/decluster — デクラスタリング
- [ ] 全テスト PASSED
