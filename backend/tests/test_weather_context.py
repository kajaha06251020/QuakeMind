import re
import pytest
from app.services.weather_context import get_weather_at_location

_OPEN_METEO_PATTERN = re.compile(r"https://api\.open-meteo\.com/v1/forecast.*")


@pytest.mark.asyncio
async def test_weather_basic(httpx_mock):
    httpx_mock.add_response(
        url=_OPEN_METEO_PATTERN,
        json={"current": {"temperature_2m": 15.0, "wind_speed_10m": 10.0, "precipitation": 0.0, "weather_code": 0}},
    )
    result = await get_weather_at_location(35.0, 139.0)
    assert result["temperature_c"] == 15.0
    assert result["secondary_hazard_risks"] == []


@pytest.mark.asyncio
async def test_weather_rain_risk(httpx_mock):
    httpx_mock.add_response(
        url=_OPEN_METEO_PATTERN,
        json={"current": {"temperature_2m": 10.0, "wind_speed_10m": 5.0, "precipitation": 20.0, "weather_code": 61}},
    )
    result = await get_weather_at_location(35.0, 139.0)
    assert "landslide_risk_elevated" in result["secondary_hazard_risks"]


@pytest.mark.asyncio
async def test_weather_error(httpx_mock):
    import httpx as hx
    httpx_mock.add_exception(hx.ConnectError("timeout"))
    result = await get_weather_at_location(35.0, 139.0)
    assert "error" in result
