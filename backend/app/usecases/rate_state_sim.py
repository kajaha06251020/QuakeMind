"""Rate-State 摩擦シミュレーション。断層の核形成過程を模擬する。"""
import math
import logging
import numpy as np

logger = logging.getLogger(__name__)


def simulate_rate_state(
    initial_stress_mpa: float = 50.0,
    normal_stress_mpa: float = 100.0,
    a: float = 0.01,
    b: float = 0.015,
    dc_m: float = 0.01,
    v0_m_s: float = 1e-9,
    duration_years: float = 100.0,
    dt_years: float = 0.1,
) -> dict:
    """Rate-State 摩擦則で断層滑りをシミュレートする。

    τ = σn * [μ0 + a * ln(V/V0) + b * ln(V0 * θ / Dc)]
    dθ/dt = 1 - V*θ/Dc (aging law)

    a < b: 速度弱化 → 地震性滑り
    a > b: 速度強化 → 安定滑り
    """
    n_steps = int(duration_years / dt_years)
    dt_sec = dt_years * 365.25 * 86400

    mu0 = initial_stress_mpa / normal_stress_mpa
    theta = dc_m / v0_m_s  # 初期状態変数
    v = v0_m_s  # 初期速度

    times = []
    velocities = []
    state_vars = []
    stresses = []

    for i in range(n_steps):
        t_years = i * dt_years

        # 摩擦係数
        mu = mu0 + a * math.log(max(v / v0_m_s, 1e-20)) + b * math.log(max(v0_m_s * theta / dc_m, 1e-20))
        stress = normal_stress_mpa * mu

        # 状態変数の更新 (aging law)
        dtheta = 1 - v * theta / dc_m
        theta += dtheta * dt_sec
        theta = max(theta, 1e-10)

        # 速度の更新（準静的近似）
        # テクトニックローディング
        loading_rate = 1e-12  # m/s (プレート速度 ~3 cm/yr)
        v = v0_m_s * math.exp((stress - initial_stress_mpa) / (a * normal_stress_mpa))
        v = min(v, 1.0)  # cap at 1 m/s
        v = max(v, 1e-15)

        times.append(round(t_years, 2))
        velocities.append(float(v))
        state_vars.append(float(theta))
        stresses.append(round(float(stress), 4))

    # 地震サイクルの検出（速度 > 0.01 m/s を地震とみなす）
    earthquake_times = [t for t, v in zip(times, velocities) if v > 0.01]

    # (a-b) の符号で安定性判定
    stability = "unstable (seismogenic)" if (a - b) < 0 else "stable (aseismic)"

    return {
        "parameters": {"a": a, "b": b, "dc_m": dc_m, "normal_stress_mpa": normal_stress_mpa},
        "a_minus_b": round(a - b, 4),
        "stability": stability,
        "duration_years": duration_years,
        "n_earthquakes_detected": len(earthquake_times),
        "earthquake_times_years": earthquake_times[:20],  # 最大20件
        "timeseries_sample": [
            {"year": times[i], "velocity_m_s": velocities[i], "stress_mpa": stresses[i]}
            for i in range(0, len(times), max(1, len(times) // 20))
        ],
    }
