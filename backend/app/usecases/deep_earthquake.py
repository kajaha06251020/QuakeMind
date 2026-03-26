"""深発地震分類器+メカニズム推定。深度・温度・圧力から可能なメカニズムを推論。"""
import math, logging

logger = logging.getLogger(__name__)

# 地球内部の温度・圧力プロファイル（簡易）
def _temperature_at_depth(depth_km: float) -> float:
    """深度における温度 (°C) の推定。"""
    if depth_km < 100: return 15 + depth_km * 10
    if depth_km < 300: return 1000 + (depth_km - 100) * 3
    return 1600 + (depth_km - 300) * 1.5

def _pressure_at_depth(depth_km: float) -> float:
    """深度における圧力 (GPa) の推定。"""
    return depth_km * 0.033  # 約33 MPa/km


def classify_deep_mechanism(depth_km: float, magnitude: float) -> dict:
    """深発地震のメカニズムを推定する。"""
    temp = _temperature_at_depth(depth_km)
    pressure = _pressure_at_depth(depth_km)

    mechanisms = []

    if depth_km < 70:
        mechanisms.append({"type": "brittle_fracture", "probability": 0.9, "description": "脆性破壊。通常の摩擦滑り。"})

    elif 70 <= depth_km < 300:
        # 遷移帯: 脱水脆化 + 塑性変形
        if temp < 800:
            mechanisms.append({"type": "dehydration_embrittlement", "probability": 0.6, "description": "脱水脆化。含水鉱物（蛇紋石等）の脱水反応で間隙水圧上昇→破壊。"})
        mechanisms.append({"type": "thermal_shear", "probability": 0.3, "description": "熱せん断不安定。高速変形→局所的加熱→強度低下→不安定滑り。"})
        if pressure > 5:
            mechanisms.append({"type": "plastic_instability", "probability": 0.2, "description": "塑性不安定。高圧下での結晶粒界滑りの局在化。"})

    elif 300 <= depth_km < 500:
        mechanisms.append({"type": "olivine_metastable", "probability": 0.5, "description": "準安定オリビンくさび。沈み込むスラブ内で低温維持されたオリビンが相転移。"})
        mechanisms.append({"type": "dehydration_embrittlement", "probability": 0.3, "description": "深部脱水。高圧含水鉱物の分解。"})
        mechanisms.append({"type": "thermal_shear", "probability": 0.2, "description": "熱せん断不安定。"})

    else:  # > 500km
        mechanisms.append({"type": "phase_transition", "probability": 0.6, "description": "相転移誘発破壊。オリビン→スピネル（リングウッダイト）の相転移。体積変化が応力集中を生む。"})
        mechanisms.append({"type": "transformational_faulting", "probability": 0.3, "description": "変態断層。相転移が薄いゾーンに局在化し、断層のように滑る。"})

    mechanisms.sort(key=lambda m: m["probability"], reverse=True)

    # 研究上の意義
    research_significance = []
    if depth_km > 300:
        research_significance.append("深発地震のメカニズムは地震学の未解決問題の一つ")
    if depth_km > 500:
        research_significance.append("下部マントルでの地震は相転移のダイナミクスを理解する手がかり")
    if magnitude > 7 and depth_km > 300:
        research_significance.append(f"M{magnitude}の深発大地震は稀。破壊過程の詳細研究が必要")

    return {
        "depth_km": depth_km, "magnitude": magnitude,
        "estimated_temperature_c": round(temp, 0), "estimated_pressure_gpa": round(pressure, 1),
        "most_likely_mechanism": mechanisms[0]["type"],
        "mechanisms": mechanisms,
        "research_significance": research_significance,
        "is_anomalous": depth_km > 300 and magnitude > 6,
    }
