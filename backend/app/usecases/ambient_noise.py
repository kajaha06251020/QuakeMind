"""アンビエントノイズ変化検出。速度構造の時間変化を推定する。"""
import logging
import numpy as np
logger = logging.getLogger(__name__)

def detect_velocity_change(correlation_functions: list[np.ndarray] | None = None, reference_period: int = 30, current_period: int = 7) -> dict:
    """相互相関関数の時間変化から地下速度構造の変化を検出する。
    データがない場合はフレームワークの説明を返す。"""
    if correlation_functions is None or len(correlation_functions) < 2:
        return {
            "status": "framework_only",
            "description": "アンビエントノイズ・トモグラフィーは、地震間の背景雑音の相互相関から地下速度構造を推定する手法。速度変化（dv/v）が地震前に検出された事例が報告されている。",
            "required_data": "連続波形データの相互相関関数（日別）",
            "reference": "Brenguier et al. (2008) Science",
        }
    # 相互相関の変化率
    ref = np.mean(correlation_functions[:reference_period], axis=0)
    cur = np.mean(correlation_functions[-current_period:], axis=0)
    if np.linalg.norm(ref) == 0: return {"error": "参照期間のデータが無効"}
    cc = float(np.corrcoef(ref, cur)[0,1])
    dv_v = (1-cc)*100  # 概算
    return {"velocity_change_percent": round(dv_v,4), "correlation_coefficient": round(cc,6), "anomalous": dv_v > 0.1, "reference_days": reference_period, "current_days": current_period}
