# Phase C2: クラスタリング + 異常検知 + 静穏化検出 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** DBSCAN時空間クラスタリング、ポアソン異常検知、静穏化検出の3アルゴリズムを実装し API で公開する。

**Architecture:** `clustering.py` が DBSCAN、`anomaly_detection.py` が異常検知+静穏化を担当。`advanced_analysis_router.py` が3つの GET エンドポイントを提供。全て `db.get_events_as_records()` 経由で earthquake_events のデータを使用。

**Tech Stack:** Python 3.12+, scikit-learn (DBSCAN), scipy (poisson), numpy, FastAPI

**Spec:** `docs/superpowers/specs/2026-03-26-phase-c2-clustering-anomaly-design.md`

---

## Task 1: clustering.py（DBSCAN 時空間クラスタリング）

**Files:**
- Create: `backend/app/usecases/clustering.py`
- Create: `backend/tests/test_clustering.py`

- [ ] **Step 1.1: テストを作成する**

`backend/tests/test_clustering.py`:

```python
"""時空間クラスタリングのテスト。"""
import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.clustering import detect_clusters


def _make_clustered_events() -> list[EarthquakeRecord]:
    """2つのクラスタ + ノイズを生成。"""
    events = []
    base = datetime(2026, 3, 1, tzinfo=timezone.utc)
    # クラスタ1: 東京付近、3日間で5イベント
    for i in range(5):
        events.append(EarthquakeRecord(
            event_id=f"c1-{i}", magnitude=3.0 + i * 0.1,
            latitude=35.68 + i * 0.01, longitude=139.76 + i * 0.01,
            depth_km=20.0, timestamp=(base + timedelta(hours=i * 12)).isoformat(),
        ))
    # クラスタ2: 大阪付近、3日間で4イベント
    for i in range(4):
        events.append(EarthquakeRecord(
            event_id=f"c2-{i}", magnitude=4.0,
            latitude=34.69 + i * 0.01, longitude=135.50 + i * 0.01,
            depth_km=30.0, timestamp=(base + timedelta(days=10, hours=i * 12)).isoformat(),
        ))
    # ノイズ: 離れた場所
    events.append(EarthquakeRecord(
        event_id="noise-0", magnitude=2.5,
        latitude=43.0, longitude=141.0,
        depth_km=50.0, timestamp=(base + timedelta(days=5)).isoformat(),
    ))
    return events


def test_detect_clusters_finds_groups():
    events = _make_clustered_events()
    result = detect_clusters(events)
    assert result["n_clusters"] >= 1
    assert len(result["clusters"]) == result["n_clusters"]


def test_detect_clusters_has_required_fields():
    events = _make_clustered_events()
    result = detect_clusters(events)
    for c in result["clusters"]:
        assert "cluster_id" in c
        assert "n_events" in c
        assert "center_lat" in c
        assert "center_lon" in c
        assert "max_magnitude" in c


def test_detect_clusters_too_few_events():
    events = [EarthquakeRecord(
        event_id="solo", magnitude=3.0, latitude=35.0, longitude=139.0,
        depth_km=10.0, timestamp="2026-03-01T00:00:00+00:00",
    )]
    result = detect_clusters(events)
    assert result["n_clusters"] == 0


def test_detect_clusters_noise_count():
    events = _make_clustered_events()
    result = detect_clusters(events)
    assert result["noise_events"] >= 0
    total = sum(c["n_events"] for c in result["clusters"]) + result["noise_events"]
    assert total == len(events)
```

- [ ] **Step 1.2: clustering.py を実装する**

`backend/app/usecases/clustering.py`:

```python
"""DBSCAN 時空間クラスタリング（群発地震検知）。"""
import logging
import math
from datetime import datetime, timezone

import numpy as np
from sklearn.cluster import DBSCAN

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)

_KM_PER_DEG = 111.0  # 緯度1度 ≈ 111km


def _parse_ts(e: EarthquakeRecord) -> float:
    try:
        dt = datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return 0.0


def detect_clusters(
    events: list[EarthquakeRecord],
    spatial_km: float = 50.0,
    temporal_days: float = 7.0,
    min_samples: int = 3,
) -> dict:
    """
    DBSCAN で時空間クラスタリングを実行する。

    Args:
        events: 地震イベントリスト
        spatial_km: 空間的な近傍半径 (km)
        temporal_days: 時間的な近傍半径 (日)
        min_samples: クラスタの最小イベント数

    Returns:
        {"n_clusters": int, "noise_events": int, "clusters": [...]}
    """
    if len(events) < min_samples:
        return {"n_clusters": 0, "noise_events": len(events), "clusters": []}

    # 特徴行列: [lat_km, lon_km, time_days]
    lats = np.array([e.latitude for e in events])
    lons = np.array([e.longitude for e in events])
    times = np.array([_parse_ts(e) for e in events])

    lat_km = lats * _KM_PER_DEG
    lon_km = lons * _KM_PER_DEG * np.cos(np.radians(np.mean(lats)))
    time_days = (times - times.min()) / 86400.0

    # 正規化: spatial_km と temporal_days を同じスケールに
    X = np.column_stack([
        lat_km / spatial_km,
        lon_km / spatial_km,
        time_days / temporal_days,
    ])

    db = DBSCAN(eps=1.0, min_samples=min_samples, metric="euclidean")
    labels = db.fit_predict(X)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    noise_count = int(np.sum(labels == -1))

    clusters = []
    for cid in range(n_clusters):
        mask = labels == cid
        cluster_events = [e for e, m in zip(events, mask) if m]
        cluster_lats = lats[mask]
        cluster_lons = lons[mask]
        cluster_times = times[mask]
        cluster_mags = np.array([e.magnitude for e in cluster_events])

        clusters.append({
            "cluster_id": cid,
            "n_events": len(cluster_events),
            "center_lat": round(float(cluster_lats.mean()), 4),
            "center_lon": round(float(cluster_lons.mean()), 4),
            "start": datetime.fromtimestamp(float(cluster_times.min()), tz=timezone.utc).isoformat(),
            "end": datetime.fromtimestamp(float(cluster_times.max()), tz=timezone.utc).isoformat(),
            "max_magnitude": round(float(cluster_mags.max()), 1),
            "event_ids": [e.event_id for e in cluster_events],
        })

    # クラスタサイズ降順でソート
    clusters.sort(key=lambda c: c["n_events"], reverse=True)

    return {"n_clusters": n_clusters, "noise_events": noise_count, "clusters": clusters}
```

- [ ] **Step 1.3: pip install scikit-learn (if not installed)**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/pip install scikit-learn
```

- [ ] **Step 1.4: テスト実行**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_clustering.py -v
```

期待: 4件 PASSED

- [ ] **Step 1.5: コミット**

```bash
git add backend/app/usecases/clustering.py backend/tests/test_clustering.py
git commit -m "feat(usecases): add DBSCAN spatiotemporal earthquake clustering"
```

---

## Task 2: anomaly_detection.py（異常検知 + 静穏化）

**Files:**
- Create: `backend/app/usecases/anomaly_detection.py`
- Create: `backend/tests/test_anomaly_detection.py`

- [ ] **Step 2.1: テストを作成する**

`backend/tests/test_anomaly_detection.py`:

```python
"""異常検知 + 静穏化検出のテスト。"""
import pytest
from datetime import datetime, timezone, timedelta
from app.domain.seismology import EarthquakeRecord
from app.usecases.anomaly_detection import detect_anomaly, detect_quiescence


def _make_normal_events(n: int = 60, days: int = 60) -> list[EarthquakeRecord]:
    """均等に分布したイベント（正常活動）。"""
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        EarthquakeRecord(
            event_id=f"norm-{i}", magnitude=3.0,
            latitude=35.0, longitude=139.0, depth_km=20.0,
            timestamp=(base + timedelta(days=i)).isoformat(),
        )
        for i in range(n)
    ]


def _make_anomalous_events() -> list[EarthquakeRecord]:
    """直近7日に大量のイベントが集中。"""
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = []
    # 背景: 53日間で1件/日
    for i in range(53):
        events.append(EarthquakeRecord(
            event_id=f"bg-{i}", magnitude=3.0,
            latitude=35.0, longitude=139.0, depth_km=20.0,
            timestamp=(base + timedelta(days=i)).isoformat(),
        ))
    # 直近7日: 1日10件
    for i in range(70):
        events.append(EarthquakeRecord(
            event_id=f"anom-{i}", magnitude=3.0,
            latitude=35.0, longitude=139.0, depth_km=20.0,
            timestamp=(base + timedelta(days=53 + i / 10)).isoformat(),
        ))
    return events


def _make_quiescent_events() -> list[EarthquakeRecord]:
    """直近30日で活動が激減。"""
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = []
    # 前半150日: 1件/日
    for i in range(150):
        events.append(EarthquakeRecord(
            event_id=f"active-{i}", magnitude=3.0,
            latitude=35.0, longitude=139.0, depth_km=20.0,
            timestamp=(base + timedelta(days=i)).isoformat(),
        ))
    # 直近30日: 2件のみ
    for i in range(2):
        events.append(EarthquakeRecord(
            event_id=f"quiet-{i}", magnitude=3.0,
            latitude=35.0, longitude=139.0, depth_km=20.0,
            timestamp=(base + timedelta(days=155 + i * 10)).isoformat(),
        ))
    return events


def test_anomaly_normal():
    events = _make_normal_events()
    result = detect_anomaly(events, evaluation_days=7)
    assert result["is_anomalous"] is False


def test_anomaly_detected():
    events = _make_anomalous_events()
    result = detect_anomaly(events, evaluation_days=7)
    assert result["is_anomalous"] is True
    assert result["p_value"] < 0.05
    assert result["recent_rate"] > result["background_rate"]


def test_anomaly_insufficient_data():
    events = [EarthquakeRecord(
        event_id="x", magnitude=3.0, latitude=35.0, longitude=139.0,
        depth_km=10.0, timestamp="2026-03-01T00:00:00+00:00",
    )]
    result = detect_anomaly(events)
    assert result["is_anomalous"] is False


def test_quiescence_normal():
    events = _make_normal_events()
    result = detect_quiescence(events, evaluation_days=30)
    assert result["is_quiescent"] is False


def test_quiescence_detected():
    events = _make_quiescent_events()
    result = detect_quiescence(events, evaluation_days=30)
    assert result["is_quiescent"] is True
    assert result["ratio"] < 0.5
```

- [ ] **Step 2.2: anomaly_detection.py を実装する**

`backend/app/usecases/anomaly_detection.py`:

```python
"""地震活動の異常検知と静穏化検出。"""
import logging
from datetime import datetime, timedelta, timezone

from scipy.stats import poisson

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def _parse_ts(e: EarthquakeRecord) -> datetime:
    try:
        return datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
    except Exception:
        return datetime(2000, 1, 1, tzinfo=timezone.utc)


def detect_anomaly(
    events: list[EarthquakeRecord],
    evaluation_days: int = 7,
) -> dict:
    """
    ポアソン分布に基づく異常活動検知。

    背景期間の平均発生率と直近N日の発生率を比較し、
    ポアソン上側確率で p < 0.05 なら異常と判定。
    """
    if len(events) < 5:
        return {
            "is_anomalous": False,
            "background_rate": 0.0,
            "recent_rate": 0.0,
            "p_value": 1.0,
            "evaluation_days": evaluation_days,
        }

    timestamps = sorted([_parse_ts(e) for e in events])
    last_time = timestamps[-1]
    cutoff = last_time - timedelta(days=evaluation_days)

    background_events = [t for t in timestamps if t < cutoff]
    recent_events = [t for t in timestamps if t >= cutoff]

    if not background_events:
        return {
            "is_anomalous": False,
            "background_rate": 0.0,
            "recent_rate": len(recent_events) / max(evaluation_days, 1),
            "p_value": 1.0,
            "evaluation_days": evaluation_days,
        }

    bg_span_days = max((cutoff - timestamps[0]).total_seconds() / 86400, 1)
    bg_rate = len(background_events) / bg_span_days  # 件/日
    recent_rate = len(recent_events) / max(evaluation_days, 1)

    # ポアソン分布: 背景発生率でevaluation_days間に期待されるイベント数
    expected = bg_rate * evaluation_days
    observed = len(recent_events)

    # 上側確率: P(X >= observed)
    p_value = 1.0 - poisson.cdf(observed - 1, expected) if expected > 0 else 1.0
    is_anomalous = p_value < 0.05 and recent_rate > bg_rate

    return {
        "is_anomalous": is_anomalous,
        "background_rate": round(bg_rate, 4),
        "recent_rate": round(recent_rate, 4),
        "p_value": round(float(p_value), 6),
        "evaluation_days": evaluation_days,
    }


def detect_quiescence(
    events: list[EarthquakeRecord],
    evaluation_days: int = 30,
) -> dict:
    """
    静穏化検出。

    背景期間の発生率に対して直近発生率が50%以下なら静穏化と判定。
    """
    if len(events) < 5:
        return {
            "is_quiescent": False,
            "background_rate": 0.0,
            "recent_rate": 0.0,
            "ratio": 1.0,
            "evaluation_days": evaluation_days,
        }

    timestamps = sorted([_parse_ts(e) for e in events])
    last_time = timestamps[-1]
    cutoff = last_time - timedelta(days=evaluation_days)

    background_events = [t for t in timestamps if t < cutoff]
    recent_events = [t for t in timestamps if t >= cutoff]

    if not background_events:
        return {
            "is_quiescent": False,
            "background_rate": 0.0,
            "recent_rate": len(recent_events) / max(evaluation_days, 1),
            "ratio": 1.0,
            "evaluation_days": evaluation_days,
        }

    bg_span_days = max((cutoff - timestamps[0]).total_seconds() / 86400, 1)
    bg_rate = len(background_events) / bg_span_days
    recent_rate = len(recent_events) / max(evaluation_days, 1)

    ratio = recent_rate / bg_rate if bg_rate > 0 else 1.0
    is_quiescent = ratio < 0.5 and len(background_events) >= 10

    return {
        "is_quiescent": is_quiescent,
        "background_rate": round(bg_rate, 4),
        "recent_rate": round(recent_rate, 4),
        "ratio": round(ratio, 4),
        "evaluation_days": evaluation_days,
    }
```

- [ ] **Step 2.3: テスト実行**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_anomaly_detection.py -v
```

期待: 5件 PASSED

- [ ] **Step 2.4: コミット**

```bash
git add backend/app/usecases/anomaly_detection.py backend/tests/test_anomaly_detection.py
git commit -m "feat(usecases): add Poisson anomaly detection and quiescence detection"
```

---

## Task 3: advanced_analysis_router.py（3エンドポイント）

**Files:**
- Create: `backend/app/interfaces/advanced_analysis_router.py`
- Create: `backend/tests/test_advanced_analysis_api.py`
- Modify: `backend/app/interfaces/api.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 3.1: テストを作成する**

`backend/tests/test_advanced_analysis_api.py`:

```python
"""高度分析 API のテスト。"""
import uuid
import pytest
import random
from datetime import datetime, timezone, timedelta

from app.infrastructure.database import get_session_factory
from app.infrastructure.models_db import EarthquakeEventDB


async def _seed_cluster_events():
    random.seed(42)
    factory = get_session_factory()
    async with factory() as session:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        # クラスタ1: 近い場所・時間に集中
        for i in range(10):
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(), event_id=f"cl-{uuid.uuid4().hex[:8]}",
                source="p2p", magnitude=round(random.uniform(2.0, 5.0), 1),
                depth_km=20.0, latitude=35.0 + random.uniform(-0.05, 0.05),
                longitude=139.0 + random.uniform(-0.05, 0.05),
                region="東京都",
                occurred_at=base + timedelta(days=random.uniform(0, 3)),
                fetched_at=datetime.now(timezone.utc),
            ))
        # 散在イベント
        for i in range(20):
            session.add(EarthquakeEventDB(
                id=uuid.uuid4(), event_id=f"sc-{uuid.uuid4().hex[:8]}",
                source="usgs", magnitude=round(random.uniform(2.0, 4.0), 1),
                depth_km=30.0, latitude=30.0 + random.uniform(0, 10),
                longitude=130.0 + random.uniform(0, 10),
                region="東京都",
                occurred_at=base + timedelta(days=random.uniform(0, 60)),
                fetched_at=datetime.now(timezone.utc),
            ))
        await session.commit()


@pytest.mark.asyncio
async def test_get_clusters(async_client, db_engine):
    await _seed_cluster_events()
    resp = await async_client.get("/analysis-advanced/clusters")
    assert resp.status_code == 200
    data = resp.json()
    assert "n_clusters" in data
    assert "clusters" in data
    assert isinstance(data["clusters"], list)


@pytest.mark.asyncio
async def test_get_anomaly(async_client, db_engine):
    await _seed_cluster_events()
    resp = await async_client.get("/analysis-advanced/anomaly?evaluation_days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_anomalous" in data
    assert "background_rate" in data
    assert "p_value" in data


@pytest.mark.asyncio
async def test_get_quiescence(async_client, db_engine):
    await _seed_cluster_events()
    resp = await async_client.get("/analysis-advanced/quiescence?evaluation_days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_quiescent" in data
    assert "ratio" in data
```

- [ ] **Step 3.2: advanced_analysis_router.py を作成する**

`backend/app/interfaces/advanced_analysis_router.py`:

```python
"""高度分析 API ルーター (Phase C2)"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.infrastructure import db
from app.usecases.clustering import detect_clusters
from app.usecases.anomaly_detection import detect_anomaly, detect_quiescence

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis-advanced", tags=["advanced-analysis"])


async def _get_records(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    from datetime import datetime as dt
    start_dt = dt.fromisoformat(start) if start else None
    end_dt = dt.fromisoformat(end) if end else None
    return await db.get_events_as_records(region=region, start=start_dt, end=end_dt)


@router.get("/clusters")
async def get_clusters(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    spatial_km: float = Query(default=50.0, ge=5.0, le=500.0),
    temporal_days: float = Query(default=7.0, ge=1.0, le=90.0),
    min_samples: int = Query(default=3, ge=2, le=20),
):
    records = await _get_records(region=region, start=start, end=end)
    if len(records) < min_samples:
        return {"n_clusters": 0, "noise_events": len(records), "clusters": []}
    return detect_clusters(records, spatial_km=spatial_km, temporal_days=temporal_days, min_samples=min_samples)


@router.get("/anomaly")
async def get_anomaly(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    evaluation_days: int = Query(default=7, ge=1, le=90),
):
    records = await _get_records(region=region, start=start, end=end)
    result = detect_anomaly(records, evaluation_days=evaluation_days)
    result["region"] = region
    return result


@router.get("/quiescence")
async def get_quiescence(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    evaluation_days: int = Query(default=30, ge=7, le=365),
):
    records = await _get_records(region=region, start=start, end=end)
    result = detect_quiescence(records, evaluation_days=evaluation_days)
    result["region"] = region
    return result
```

- [ ] **Step 3.3: api.py に router を include**

`backend/app/interfaces/api.py` の statistics_router include の後に追加:

```python
from app.interfaces.advanced_analysis_router import router as advanced_analysis_router
app.include_router(advanced_analysis_router)
```

- [ ] **Step 3.4: requirements.txt に scikit-learn を追加**

```
scikit-learn>=1.4.0
```

- [ ] **Step 3.5: テスト実行**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/test_advanced_analysis_api.py -v
```

期待: 3件 PASSED

- [ ] **Step 3.6: 全テスト実行**

```bash
cd D:/playground/QuakeMind/backend && .venv/Scripts/python -m pytest tests/ -v --ignore=tests/test_poseidon_loader.py
```

- [ ] **Step 3.7: コミット**

```bash
git add backend/app/interfaces/advanced_analysis_router.py backend/app/interfaces/api.py backend/tests/test_advanced_analysis_api.py backend/requirements.txt
git commit -m "feat(api): add clustering, anomaly detection, quiescence endpoints (C2)"
```

---

## 完了条件

- [ ] GET /analysis-advanced/clusters — DBSCAN クラスタリング
- [ ] GET /analysis-advanced/anomaly — ポアソン異常検知
- [ ] GET /analysis-advanced/quiescence — 静穏化検出
- [ ] scikit-learn が requirements.txt に追加されている
- [ ] 全テスト PASSED
