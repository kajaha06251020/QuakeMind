"""研究ワークフロー・オーケストレーション。分析を連鎖させる。"""
import logging
from datetime import datetime, timezone

from app.services.research_journal import add_entry
from app.services.hypothesis_engine import create_hypothesis
from app.services.experiment_logger import track_experiment

logger = logging.getLogger(__name__)


async def investigate_anomaly(region: str | None = None):
    """異常検知 → b値調査 → クラスタリング → 類似検索 → レポート生成。"""
    from app.infrastructure import db
    from app.usecases.anomaly_detection import detect_anomaly
    from app.usecases.b_value_tracker import compute_b_value_timeseries
    from app.usecases.clustering import detect_clusters
    from app.usecases.similar_search import find_similar_events

    records = await db.get_events_as_records(region=region)
    if len(records) < 10:
        return {"status": "insufficient_data", "region": region}

    results = {"region": region, "steps": []}

    # Step 1: 異常検知
    anomaly = detect_anomaly(records, evaluation_days=7)
    results["anomaly"] = anomaly
    results["steps"].append("anomaly_detection")

    # Step 2: b値追跡
    timeseries = compute_b_value_timeseries(records, window_days=60, step_days=7)
    results["b_value_timeseries"] = timeseries[-3:] if timeseries else []
    results["steps"].append("b_value_tracking")

    # Step 3: クラスタリング
    clusters = detect_clusters(records)
    results["clusters"] = {"n_clusters": clusters["n_clusters"]}
    results["steps"].append("clustering")

    # Step 4: 最大イベントの類似検索
    if records:
        max_event = max(records, key=lambda e: e.magnitude)
        similar = find_similar_events(max_event, records, max_results=3)
        results["similar_events"] = similar
        results["steps"].append("similar_search")

    # Step 5: 結果をジャーナルに記録
    summary_parts = []
    if anomaly["is_anomalous"]:
        summary_parts.append(f"異常活動検出 (p={anomaly['p_value']:.4f})")
    if timeseries:
        summary_parts.append(f"最新b値: {timeseries[-1]['b_value']:.2f}")
    if clusters["n_clusters"] > 0:
        summary_parts.append(f"{clusters['n_clusters']}クラスタ検出")

    summary = " / ".join(summary_parts) if summary_parts else "特筆すべき異常なし"

    await add_entry(
        "report",
        f"異常調査レポート: {region or '全域'}",
        summary,
        region=region,
        metadata={"anomaly": anomaly["is_anomalous"], "n_clusters": clusters["n_clusters"]},
    )

    results["summary"] = summary
    return results


async def investigate_large_earthquake(event_id: str):
    """大地震発生時の自動詳細分析。"""
    from app.infrastructure import db
    from app.usecases.etas import etas_forecast
    from app.usecases.shakemap import compute_shakemap
    from app.usecases.tsunami_arrival import estimate_tsunami_arrival
    from app.usecases.damage_estimation import estimate_damage

    records = await db.get_events_as_records()
    target = next((r for r in records if r.event_id == event_id), None)
    if not target:
        return {"error": f"イベント {event_id} が見つかりません"}

    results = {"event_id": event_id, "magnitude": target.magnitude}

    # ETAS予測
    results["etas_forecast"] = etas_forecast(records, forecast_hours=72)

    # ShakeMap
    results["shakemap_summary"] = {
        "grid_points": len(compute_shakemap(target.latitude, target.longitude, target.depth_km, target.magnitude)["grid"])
    }

    # 津波
    results["tsunami"] = estimate_tsunami_arrival(target.latitude, target.longitude, target.depth_km, target.magnitude)

    # 被害推定
    results["damage"] = estimate_damage(target.latitude, target.longitude, target.depth_km, target.magnitude)

    # ジャーナル記録
    await add_entry(
        "report",
        f"大地震詳細分析: M{target.magnitude} {event_id}",
        f"ETAS予測: {results['etas_forecast']['expected_events']}件/72h, 被害レベル: {results['damage']['damage_level']}",
        metadata={"event_id": event_id, "magnitude": target.magnitude},
    )

    # 仮説生成
    if target.magnitude >= 6.0:
        await create_hypothesis(
            f"M{target.magnitude}の余震活動パターン",
            f"{event_id} の余震がETAS予測通りに減衰するか検証",
            trigger_event=f"large_earthquake_{event_id}",
            verify_after_days=14,
        )

    return results
