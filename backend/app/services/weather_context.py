"""気象コンテキスト。地震発生時の気象条件を取得し二次災害リスクを評価する。

Windy.com の有料 API の代わりに、Open-Meteo（無料）を使用。
"""
import logging
import httpx

logger = logging.getLogger(__name__)

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


async def get_weather_at_location(latitude: float, longitude: float) -> dict:
    """指定座標の現在の気象条件を取得する。"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_OPEN_METEO_URL, params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,wind_speed_10m,precipitation,weather_code",
            })
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error("[Weather] API エラー: %s", e)
        return {"error": str(e)}

    current = data.get("current", {})

    # 二次災害リスク評価
    precipitation = current.get("precipitation", 0)
    wind_speed = current.get("wind_speed_10m", 0)

    risks = []
    if precipitation and precipitation > 5:
        risks.append("landslide_risk_elevated")  # 降雨→地滑りリスク
    if wind_speed and wind_speed > 40:
        risks.append("fire_spread_risk")  # 強風→火災延焼リスク

    return {
        "latitude": latitude,
        "longitude": longitude,
        "temperature_c": current.get("temperature_2m"),
        "wind_speed_kmh": wind_speed,
        "precipitation_mm": precipitation,
        "weather_code": current.get("weather_code"),
        "secondary_hazard_risks": risks,
    }
