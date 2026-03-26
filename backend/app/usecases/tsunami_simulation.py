"""津波数値シミュレーション。浅水方程式の簡易差分法。"""
import math, logging
import numpy as np
logger = logging.getLogger(__name__)

def simulate_tsunami_propagation(source_lat: float, source_lon: float, magnitude: float, depth_km: float, grid_size: int = 50, dt_seconds: float = 30, total_minutes: int = 60) -> dict:
    if magnitude < 6.5 or depth_km > 60: return {"tsunami_generated": False, "message": "津波発生条件を満たさない"}
    g = 9.81; dx = 5000  # 5km grid
    h = np.full((grid_size, grid_size), 2000.0)  # 平均水深2000m
    eta = np.zeros((grid_size, grid_size))  # 水位
    u = np.zeros((grid_size, grid_size)); v = np.zeros((grid_size, grid_size))
    # 初期変位（楕円モデル）
    cx, cy = grid_size//2, grid_size//2
    slip_m = 10**(0.5*magnitude-1.8)
    for i in range(grid_size):
        for j in range(grid_size):
            r = math.sqrt((i-cx)**2+(j-cy)**2)*dx/1000
            if r < magnitude*20: eta[i,j] = slip_m*0.5*math.exp(-r**2/(magnitude*10)**2)
    n_steps = int(total_minutes*60/dt_seconds)
    max_heights = []
    for step in range(min(n_steps, 200)):
        eta_new = eta.copy()
        for i in range(1,grid_size-1):
            for j in range(1,grid_size-1):
                eta_new[i,j] = eta[i,j]-dt_seconds*h[i,j]*((u[i+1,j]-u[i-1,j])/(2*dx)+(v[i,j+1]-v[i,j-1])/(2*dx))
                u[i,j] -= dt_seconds*g*(eta[i+1,j]-eta[i-1,j])/(2*dx)
                v[i,j] -= dt_seconds*g*(eta[i,j+1]-eta[i,j-1])/(2*dx)
        eta = eta_new
        max_heights.append(round(float(np.max(np.abs(eta))),2))
    return {"tsunami_generated": True, "initial_displacement_m": round(float(slip_m*0.5),2), "max_wave_height_m": round(max(max_heights),2), "simulation_minutes": total_minutes, "grid_size": grid_size, "propagation_snapshots": max_heights[::10]}
