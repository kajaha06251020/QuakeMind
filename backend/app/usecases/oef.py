"""Operational Earthquake Forecasting (OEF) フレームワーク。

INGV 方式の確率予報。24h/7d/30d の確率予報を生成する。
"""
import logging
from datetime import datetime, timezone

from app.domain.seismology import EarthquakeRecord
from app.usecases.etas import etas_forecast
from app.usecases.ml_predictor import predict_large_earthquake
from app.usecases.anomaly_detection import detect_anomaly
from app.usecases.ensemble import bayesian_model_averaging

logger = logging.getLogger(__name__)

# デフォルトのモデル重み（ベイズ更新で変化する）
_DEFAULT_WEIGHTS = {"etas": 2.0, "ml": 1.0, "anomaly": 0.5}


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


async def generate_oef_forecast(
    events: list[EarthquakeRecord],
    magnitude_threshold: float = 5.0,
    model_weights: dict | None = None,
) -> dict:
    """OEF 確率予報を生成する。

    Returns:
        24h/7d/30d の確率予報 + 各モデルの詳細
    """
    if len(events) < 10:
        return {"error": "イベント数不足", "n_events": len(events)}

    weights = model_weights or _DEFAULT_WEIGHTS
    forecasts = {}

    for hours, label in [(24, "24h"), (168, "7d"), (720, "30d")]:
        # ETAS予測
        etas = etas_forecast(events, forecast_hours=hours, m_threshold=magnitude_threshold)
        etas_prob = etas.get("probability_m4_plus", 0)

        # ML予測
        ml = predict_large_earthquake(events, magnitude_threshold=magnitude_threshold)
        ml_prob = ml.get("probability", 0)

        # 異常検知ベースの確率補正
        days = hours // 24
        anomaly = detect_anomaly(events, evaluation_days=max(1, days))
        anomaly_factor = 1.5 if anomaly.get("is_anomalous") else 1.0
        anomaly_prob = _clamp(etas_prob * anomaly_factor)

        # BMA 統合
        model_preds = [
            {"name": "etas", "probability": _clamp(etas_prob), "weight": weights.get("etas", 1), "uncertainty": 0.15},
            {"name": "ml", "probability": _clamp(ml_prob), "weight": weights.get("ml", 1), "uncertainty": 0.2},
            {"name": "anomaly_adjusted", "probability": _clamp(anomaly_prob), "weight": weights.get("anomaly", 0.5), "uncertainty": 0.25},
        ]

        ensemble = bayesian_model_averaging(model_preds)

        forecasts[label] = {
            "probability": ensemble["ensemble_probability"],
            "uncertainty": ensemble["uncertainty"],
            "ci_95": ensemble["ci_95"],
            "model_contributions": ensemble["model_contributions"],
            "anomaly_active": anomaly.get("is_anomalous", False),
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "magnitude_threshold": magnitude_threshold,
        "n_events_analyzed": len(events),
        "forecasts": forecasts,
        "model_weights_used": weights,
    }
