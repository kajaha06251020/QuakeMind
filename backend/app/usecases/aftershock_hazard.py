"""確率的余震ハザード。余震による揺れのハザードを直接計算。"""
import math, logging
import numpy as np
from app.domain.seismology import EarthquakeRecord
from app.usecases.etas import etas_forecast
logger = logging.getLogger(__name__)

def compute_aftershock_hazard(events: list[EarthquakeRecord], site_lat: float, site_lon: float, forecast_hours: int = 72) -> dict:
    if not events: return {"error": "イベントなし"}
    forecast = etas_forecast(events, forecast_hours=forecast_hours)
    expected = forecast.get("expected_events", 0)
    # 各マグニチュードビンでの期待数 × 距離減衰 → 揺れの確率
    b = 1.0; mc = 2.0
    intensities = {"3": 0, "4": 0, "5": 0, "6": 0}
    for m in np.arange(mc, 8.0, 0.5):
        rate_m = expected * 10**(-b*(m-mc)) * (1-10**(-b*0.5))
        for e in events[-5:]:  # 最新5件の位置を使用
            dist = math.sqrt(((site_lat-e.latitude)*111)**2+((site_lon-e.longitude)*111*math.cos(math.radians(site_lat)))**2)
            R = math.sqrt(dist**2+e.depth_km**2)
            intensity = 2.68+1.0*m-1.58*math.log10(max(R,1))
            for threshold in ["3","4","5","6"]:
                if intensity >= float(threshold):
                    intensities[threshold] += rate_m/max(len(events[-5:]),1)
    hazard = {f"intensity_{k}_plus": round(min(1, 1-math.exp(-v)), 4) for k, v in intensities.items()}
    return {"site": {"latitude": site_lat, "longitude": site_lon}, "forecast_hours": forecast_hours, "expected_aftershocks": round(expected, 1), "hazard_probabilities": hazard}
