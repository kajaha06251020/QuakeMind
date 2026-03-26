"""GNSS 地殻変動モニタリング。

国土地理院の電子基準点データを参照する。
実際のデータダウンロードは登録が必要なため、分析フレームワークのみ実装。
"""
import logging
import math

logger = logging.getLogger(__name__)

# 主要な電子基準点（GEONET）— 代表的な観測点
_REFERENCE_STATIONS = [
    {"id": "940054", "name": "三浦", "lat": 35.17, "lon": 139.62},
    {"id": "960534", "name": "銚子", "lat": 35.74, "lon": 140.86},
    {"id": "020986", "name": "女川", "lat": 38.45, "lon": 141.44},
    {"id": "950242", "name": "御前崎", "lat": 34.63, "lon": 138.22},
    {"id": "970838", "name": "潮岬", "lat": 33.45, "lon": 135.76},
]

# 国土地理院 GNSS データ参照 URL
_GSI_URL = "https://terras.gsi.go.jp/"


def get_gnss_stations() -> dict:
    """電子基準点リストと参照URLを返す。"""
    return {
        "reference_url": _GSI_URL,
        "description": "国土地理院 電子基準点（GEONET）データ。実データの取得には terras.gsi.go.jp での登録が必要。",
        "stations": _REFERENCE_STATIONS,
        "n_stations": len(_REFERENCE_STATIONS),
    }


def analyze_displacement(
    station_id: str,
    displacements: list[dict],  # [{"date": "YYYY-MM-DD", "east_mm": float, "north_mm": float, "up_mm": float}]
) -> dict:
    """変位データから異常を検出する（フレームワーク）。

    displacements を外部から渡す設計（データ取得は手動/別ツール）。
    """
    if not displacements:
        return {"station_id": station_id, "anomaly_detected": False, "message": "データなし"}

    # 変位の大きさを計算
    magnitudes = []
    for d in displacements:
        e = d.get("east_mm", 0)
        n = d.get("north_mm", 0)
        u = d.get("up_mm", 0)
        magnitudes.append(math.sqrt(e**2 + n**2 + u**2))

    avg = sum(magnitudes) / len(magnitudes) if magnitudes else 0
    max_disp = max(magnitudes) if magnitudes else 0

    # 閾値: 日常変動は ~1mm/日、異常は > 10mm/日
    anomaly = max_disp > 10.0

    return {
        "station_id": station_id,
        "n_observations": len(displacements),
        "avg_displacement_mm": round(avg, 2),
        "max_displacement_mm": round(max_disp, 2),
        "anomaly_detected": anomaly,
        "threshold_mm": 10.0,
    }
