"""自律研究スケジューラー。定期的に分析パイプラインを自動実行する。"""
import asyncio
import logging
from datetime import datetime, timezone

from app.services.research_journal import add_entry
from app.services.experiment_logger import track_experiment

logger = logging.getLogger(__name__)


async def hourly_analysis():
    """毎時実行: データ取得→異常検知→ジャーナル記録。"""
    from app.infrastructure import db
    from app.usecases.anomaly_detection import detect_anomaly

    records = await db.get_events_as_records()
    if not records:
        return {"status": "no_data"}

    async with track_experiment("hourly_analysis", {"n_events": len(records)}) as exp:
        anomaly = detect_anomaly(records, evaluation_days=1)

        if anomaly["is_anomalous"]:
            await add_entry(
                "anomaly",
                f"異常活動検出: p={anomaly['p_value']:.4f}",
                f"直近1日の発生率 {anomaly['recent_rate']:.2f}/日 が背景 {anomaly['background_rate']:.2f}/日 を有意に上回る",
                metadata=anomaly,
            )

        exp["results"] = {"anomaly_detected": anomaly["is_anomalous"], "n_events": len(records)}
    return anomaly


async def daily_analysis():
    """毎日実行: b値追跡→クラスタリング→仮説チェック→レポート生成。"""
    from app.infrastructure import db
    from app.usecases.b_value_tracker import compute_b_value_timeseries
    from app.usecases.clustering import detect_clusters
    from app.services.hypothesis_engine import check_expired_hypotheses, create_hypothesis
    from app.services.pattern_memory import store_pattern

    records = await db.get_events_as_records()
    if len(records) < 10:
        return {"status": "insufficient_data"}

    results = {}

    async with track_experiment("daily_b_value", {"n_events": len(records)}) as exp:
        timeseries = compute_b_value_timeseries(records, window_days=60, step_days=7)

        if len(timeseries) >= 2:
            latest_b = timeseries[-1]["b_value"]
            prev_b = timeseries[-2]["b_value"]
            b_change = latest_b - prev_b

            if b_change < -0.2:
                await add_entry(
                    "finding",
                    f"b値急低下: {prev_b:.2f} → {latest_b:.2f}",
                    f"b値が {abs(b_change):.2f} 低下。大地震の前兆の可能性を監視。",
                    metadata={"b_values": timeseries[-3:]},
                )
                await create_hypothesis(
                    f"b値低下({latest_b:.2f})は大地震の前兆",
                    f"b値が{prev_b:.2f}から{latest_b:.2f}に低下。30日以内にM5以上が発生するか検証。",
                    trigger_event="b_value_drop",
                    verify_after_days=30,
                )

            results["b_value_latest"] = latest_b
            results["b_value_change"] = round(b_change, 3)

        exp["results"] = results

    # クラスタリング
    async with track_experiment("daily_clustering", {"n_events": len(records)}) as exp:
        clusters = detect_clusters(records)
        if clusters["n_clusters"] > 0:
            for cl in clusters["clusters"]:
                vector = [cl["center_lat"], cl["center_lon"], cl["n_events"], cl["max_magnitude"]]
                store_pattern(f"cluster_{datetime.now(timezone.utc).strftime('%Y%m%d')}", vector, cl)

            await add_entry(
                "finding",
                f"{clusters['n_clusters']}個の地震クラスタを検出",
                f"最大クラスタ: {clusters['clusters'][0]['n_events']}イベント, M{clusters['clusters'][0]['max_magnitude']}",
                metadata={"n_clusters": clusters["n_clusters"]},
            )
        results["n_clusters"] = clusters["n_clusters"]
        exp["results"] = {"n_clusters": clusters["n_clusters"]}

    # 仮説期限チェック
    expired = await check_expired_hypotheses()
    results["expired_hypotheses"] = expired

    return results


async def weekly_analysis():
    """毎週実行: ETAS再推定→リスクプロファイル→包括レポート。"""
    from app.infrastructure import db
    from app.usecases.etas_mle import estimate_etas_parameters
    from app.usecases.risk_profile import compute_risk_profile

    records = await db.get_events_as_records()
    if len(records) < 20:
        return {"status": "insufficient_data"}

    results = {}

    async with track_experiment("weekly_etas_mle", {"n_events": len(records)}) as exp:
        etas = estimate_etas_parameters(records)
        results["etas"] = etas
        exp["results"] = etas

    # 主要地域のリスクプロファイル
    regions = ["東京都", "宮城県", "大阪府", "静岡県"]
    profiles = {}
    for region in regions:
        region_records = await db.get_events_as_records(region=region)
        if region_records:
            profiles[region] = compute_risk_profile(region, region_records)

    if profiles:
        await add_entry(
            "report",
            "週次リスクプロファイル更新",
            f"{len(profiles)}地域のリスクプロファイルを更新。" +
            " / ".join(f"{r}: {p['risk_level']}" for r, p in profiles.items()),
            metadata={"profiles": {r: p["risk_score"] for r, p in profiles.items()}},
        )

    results["risk_profiles"] = profiles
    return results
