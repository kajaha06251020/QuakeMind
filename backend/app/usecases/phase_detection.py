"""地震波位相検出フレームワーク。

PhaseNet/EQTransformer スタイルの P波/S波自動検出。
実モデルは外部ダウンロード前提。ここではルールベースフォールバックを実装。
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)


def detect_phases_sta_lta(
    waveform: np.ndarray,
    sampling_rate: float = 100.0,
    sta_window: float = 1.0,
    lta_window: float = 10.0,
    trigger_ratio: float = 3.0,
) -> list[dict]:
    """STA/LTA法によるP波検出（ルールベースフォールバック）。

    Args:
        waveform: 1D 振幅データ
        sampling_rate: サンプリングレート (Hz)
        sta_window: 短期平均窓 (秒)
        lta_window: 長期平均窓 (秒)
        trigger_ratio: トリガー閾値

    Returns:
        [{"type": "P", "sample": int, "time_sec": float, "confidence": float}, ...]
    """
    n = len(waveform)
    sta_len = int(sta_window * sampling_rate)
    lta_len = int(lta_window * sampling_rate)

    if n < lta_len + sta_len:
        return []

    # 包絡線（絶対値）
    envelope = np.abs(waveform)

    picks = []
    triggered = False

    for i in range(lta_len, n - sta_len):
        lta = np.mean(envelope[i - lta_len:i])
        sta = np.mean(envelope[i:i + sta_len])

        if lta <= 0:
            continue

        ratio = sta / lta

        if ratio >= trigger_ratio and not triggered:
            triggered = True
            confidence = min(1.0, (ratio - trigger_ratio) / trigger_ratio + 0.5)
            picks.append({
                "type": "P",
                "sample": i,
                "time_sec": round(i / sampling_rate, 4),
                "sta_lta_ratio": round(ratio, 2),
                "confidence": round(confidence, 4),
            })
        elif ratio < trigger_ratio * 0.5:
            triggered = False

    return picks


def estimate_s_wave(p_picks: list[dict], vp_vs_ratio: float = 1.73) -> list[dict]:
    """P波到着時刻からS波到着時刻を推定する。"""
    s_picks = []
    for p in p_picks:
        s_time = p["time_sec"] * vp_vs_ratio
        s_picks.append({
            "type": "S",
            "time_sec": round(s_time, 4),
            "estimated_from_p": True,
            "vp_vs_ratio": vp_vs_ratio,
        })
    return s_picks


def analyze_waveform(
    waveform: np.ndarray,
    sampling_rate: float = 100.0,
) -> dict:
    """波形データを総合分析する。"""
    p_picks = detect_phases_sta_lta(waveform, sampling_rate)
    s_picks = estimate_s_wave(p_picks)

    # 基本統計
    stats = {
        "n_samples": len(waveform),
        "duration_sec": round(len(waveform) / sampling_rate, 2),
        "max_amplitude": round(float(np.max(np.abs(waveform))), 4),
        "rms_amplitude": round(float(np.sqrt(np.mean(waveform ** 2))), 4),
    }

    return {
        "p_picks": p_picks,
        "s_picks": s_picks,
        "statistics": stats,
        "method": "STA/LTA (rule-based fallback)",
    }
