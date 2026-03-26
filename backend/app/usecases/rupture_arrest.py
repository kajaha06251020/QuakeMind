"""破壊停止条件シミュレーター。断層幾何学+応力不均一性で破壊がどこで止まるかを探索。"""
import math, logging
import numpy as np

logger = logging.getLogger(__name__)


def simulate_rupture_arrest(
    fault_length_km: float, fault_width_km: float,
    stress_drop_mpa: float = 3.0, n_simulations: int = 500,
    heterogeneity: float = 0.3,
) -> dict:
    """モンテカルロで破壊停止位置を探索する。

    断層を離散化し、各セルの強度にランダムな不均一性を加える。
    破壊は核形成点から伝播し、隣接セルの強度を超えられないと停止する。
    """
    rng = np.random.default_rng(42)
    nx = max(10, int(fault_length_km / 2))
    ny = max(5, int(fault_width_km / 2))

    rupture_lengths = []
    rupture_areas = []
    arrest_positions = []

    for _ in range(n_simulations):
        # 強度場（基本強度 + ランダム不均一性）
        strength = stress_drop_mpa * (1 + heterogeneity * rng.normal(0, 1, (ny, nx)))
        strength = np.maximum(strength, 0.1)

        # 応力場（核形成点で最大、距離で減衰）
        cx, cy = nx // 2, ny // 2
        stress = np.zeros((ny, nx))
        for iy in range(ny):
            for ix in range(nx):
                dist = math.sqrt((ix - cx)**2 + (iy - cy)**2) + 1
                stress[iy, ix] = stress_drop_mpa * 1.5 / dist

        # 破壊伝播（BFS）
        ruptured = np.zeros((ny, nx), dtype=bool)
        ruptured[cy, cx] = True
        queue = [(cy, cx)]

        while queue:
            y, x = queue.pop(0)
            for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                ny2, nx2 = y+dy, x+dx
                if 0 <= ny2 < ny and 0 <= nx2 < nx and not ruptured[ny2, nx2]:
                    if stress[ny2, nx2] >= strength[ny2, nx2]:
                        ruptured[ny2, nx2] = True
                        queue.append((ny2, nx2))
                        # 応力再分配
                        for dy2, dx2 in [(-1,0),(1,0),(0,-1),(0,1)]:
                            ny3, nx3 = ny2+dy2, nx2+dx2
                            if 0 <= ny3 < ny and 0 <= nx3 < nx and not ruptured[ny3, nx3]:
                                stress[ny3, nx3] += stress_drop_mpa * 0.1

        n_ruptured = int(np.sum(ruptured))
        area_km2 = n_ruptured * (fault_length_km/nx) * (fault_width_km/ny)
        length_km = int(np.sum(np.any(ruptured, axis=0))) * (fault_length_km/nx)

        rupture_lengths.append(length_km)
        rupture_areas.append(area_km2)

    lengths = np.array(rupture_lengths)
    areas = np.array(rupture_areas)

    # 等価マグニチュード
    eq_mags = [(math.log10(max(a, 0.1)) + 3.49) / 0.91 for a in areas]

    return {
        "fault_length_km": fault_length_km, "fault_width_km": fault_width_km,
        "heterogeneity": heterogeneity, "n_simulations": n_simulations,
        "rupture_length": {"mean_km": round(float(np.mean(lengths)), 1), "std_km": round(float(np.std(lengths)), 1), "p5_km": round(float(np.percentile(lengths, 5)), 1), "p95_km": round(float(np.percentile(lengths, 95)), 1)},
        "rupture_area": {"mean_km2": round(float(np.mean(areas)), 1), "p95_km2": round(float(np.percentile(areas, 95)), 1)},
        "equivalent_magnitude": {"mean": round(float(np.mean(eq_mags)), 1), "max": round(float(np.max(eq_mags)), 1), "p95": round(float(np.percentile(eq_mags, 95)), 1)},
        "full_rupture_probability": round(float(np.mean(lengths > fault_length_km * 0.8)), 4),
    }
