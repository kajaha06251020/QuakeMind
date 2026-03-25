"""POSEIDON Dataset バルクローダー。

HuggingFace Hub から地震履歴データを取得し、日本周辺に絞り込む。
リアルタイムデータではなく、統計分析・ML 学習データとして使用する。
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import settings
from app.domain.models import EarthquakeEvent

logger = logging.getLogger(__name__)

# モジュールレベルでインポートを試みる（パッチ可能にするため）
try:
    from datasets import load_dataset  # type: ignore
except ImportError:
    load_dataset = None  # type: ignore


def _parse_poseidon_row(row: dict) -> Optional[EarthquakeEvent]:
    try:
        magnitude = float(row.get("mag", -1.0))
        if magnitude < 0:
            return None

        lat = float(row.get("latitude", 0.0))
        lon = float(row.get("longitude", 0.0))
        if lat == 0.0 and lon == 0.0:
            return None

        depth_km = float(row.get("depth", 0.0))
        raw_id = str(row.get("id", "unknown"))
        event_id = f"poseidon-{raw_id}"

        time_str = row.get("time", "")
        try:
            timestamp = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            timestamp = datetime.now(timezone.utc)

        return EarthquakeEvent(
            event_id=event_id,
            magnitude=magnitude,
            depth_km=depth_km,
            latitude=lat,
            longitude=lon,
            region=str(row.get("place", "Unknown")),
            timestamp=timestamp,
            source="poseidon",
        )
    except Exception as e:
        logger.warning("[POSEIDON] パースエラー: %s", e)
        return None


def load_japan_sample() -> list[EarthquakeEvent]:
    """POSEIDON データセットから日本周辺の地震データをサンプリングする。

    注意: 初回実行時に HuggingFace からダウンロードが発生する（数 GB）。
    streaming=True によりメモリ効率的にロードする。
    """
    if not settings.poseidon_enabled:
        return []

    if load_dataset is None:
        logger.error("[POSEIDON] datasets ライブラリ未インストール: pip install datasets")
        return []

    min_lat, max_lat, min_lon, max_lon = settings.usgs_japan_bbox
    events = []

    try:
        logger.info("[POSEIDON] データセット読み込み開始: %s", settings.poseidon_dataset_name)
        dataset_dict = load_dataset(settings.poseidon_dataset_name, streaming=True)
        ds = dataset_dict["train"]

        for row in ds:
            if len(events) >= settings.poseidon_sample_limit:
                break

            event = _parse_poseidon_row(row)
            if event is None:
                continue
            if not (min_lat <= event.latitude <= max_lat and min_lon <= event.longitude <= max_lon):
                continue
            if event.magnitude < settings.magnitude_threshold:
                continue
            events.append(event)

        logger.info("[POSEIDON] 日本周辺データ %d 件ロード完了", len(events))
    except Exception as e:
        logger.error("[POSEIDON] データセット読み込みエラー: %s", e)

    return events
