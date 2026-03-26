"""震源メカニズム統合。USGSのモーメントテンソル解を取り込む。"""
import logging
import math

logger = logging.getLogger(__name__)


def parse_moment_tensor(usgs_detail: dict) -> dict | None:
    """USGS 詳細イベントデータからモーメントテンソル解を抽出する。"""
    products = usgs_detail.get("properties", {}).get("products", {})
    mt = products.get("moment-tensor", [{}])[0] if "moment-tensor" in products else None
    if not mt:
        return None

    props = mt.get("properties", {})
    return {
        "strike": float(props.get("nodal-plane-1-strike", 0)),
        "dip": float(props.get("nodal-plane-1-dip", 0)),
        "rake": float(props.get("nodal-plane-1-rake", 0)),
        "moment_magnitude": float(props.get("derived-magnitude", 0)),
        "depth_km": float(props.get("derived-depth", 0)),
        "source": "USGS moment-tensor",
    }


def classify_fault_type(rake: float) -> str:
    """レイクからの断層型分類。"""
    rake = rake % 360
    if rake > 180:
        rake -= 360
    if -30 <= rake <= 30 or 150 <= rake <= 210:
        return "strike_slip"  # 横ずれ
    elif 30 < rake < 150:
        return "reverse"  # 逆断層
    else:
        return "normal"  # 正断層


def estimate_rupture_area(magnitude: float) -> dict:
    """マグニチュードから破壊面積を推定（Wells & Coppersmith 1994）。"""
    # log10(A) = -3.49 + 0.91*M (全断層型)
    log_area = -3.49 + 0.91 * magnitude
    area_km2 = 10 ** log_area
    # 破壊長さ: log10(L) = -2.44 + 0.59*M
    log_length = -2.44 + 0.59 * magnitude
    length_km = 10 ** log_length

    return {
        "rupture_area_km2": round(area_km2, 2),
        "rupture_length_km": round(length_km, 2),
        "estimated_width_km": round(area_km2 / max(length_km, 0.1), 2),
    }
