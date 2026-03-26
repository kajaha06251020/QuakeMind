"""補助データ API ルーター (Phase B2)"""
from typing import Optional
from fastapi import APIRouter, Query
from app.services.social_search import search_social
from app.services.weather_context import get_weather_at_location
from app.services.power_outage import get_power_outage_urls

router = APIRouter(prefix="/supplementary", tags=["supplementary-data"])


@router.get("/social-search")
async def social_search(keyword: str = Query(default="地震"), limit: int = Query(default=20, ge=1, le=100)):
    return await search_social(keyword, limit)


@router.get("/weather")
async def weather(lat: float = Query(...), lon: float = Query(...)):
    return await get_weather_at_location(lat, lon)


@router.get("/power-outage")
async def power_outage(region: Optional[str] = None):
    return get_power_outage_urls(region)
