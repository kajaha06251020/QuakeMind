"""確率的地震ナウキャスティング。「今この瞬間」のハザードをリアルタイム推定。"""
import math, logging
from datetime import datetime, timezone, timedelta
from collections import Counter
import numpy as np
from app.domain.seismology import EarthquakeRecord
logger = logging.getLogger(__name__)

def nowcast(events: list[EarthquakeRecord], magnitude_threshold: float = 5.0) -> dict:
    if len(events) < 10: return {"error": "最低10イベント必要"}
    def _ts(e):
        try: return datetime.fromisoformat(e.timestamp.replace("Z","+00:00"))
        except: return datetime(2000,1,1,tzinfo=timezone.utc)
    sorted_e = sorted(events, key=_ts); timestamps = [_ts(e) for e in sorted_e]
    now = timestamps[-1]
    # 直近7日の発生率
    recent = [e for e,t in zip(sorted_e,timestamps) if (now-t).total_seconds() < 7*86400]
    recent_rate = len(recent) / 7.0
    # 全期間の平均率
    span_days = max((timestamps[-1]-timestamps[0]).total_seconds()/86400, 1)
    bg_rate = len(events) / span_days
    # 確率利得
    gain = recent_rate / max(bg_rate, 0.01)
    # M>=threshold の条件付き確率（GR則）
    b = 1.0
    p_large_daily = recent_rate * 10**(-b*(magnitude_threshold-2.0))
    p_large_7day = 1 - math.exp(-p_large_daily * 7)
    alert = "elevated" if gain > 2 else "advisory" if gain > 1.5 else "normal"
    return {"current_rate_per_day": round(recent_rate,2), "background_rate_per_day": round(bg_rate,2), "probability_gain": round(gain,2), "probability_m5_7day": round(min(p_large_7day,1),4), "alert_level": alert, "as_of": now.isoformat()}
