"""補助データ API ルーター (Phase B2/B3)"""
from typing import Optional
from fastapi import APIRouter, Query
from app.services.social_search import search_social
from app.services.weather_context import get_weather_at_location
from app.services.power_outage import get_power_outage_urls
from app.services.gnss_monitor import get_gnss_stations, analyze_displacement
from app.services.geomagnetic_monitor import get_geomagnetic_info, analyze_geomagnetic
from app.services.traffic_info import get_traffic_info_urls, estimate_road_impact
from app.infrastructure import db

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


@router.get("/gnss-stations")
async def gnss_stations():
    return get_gnss_stations()


@router.post("/gnss-analyze")
async def gnss_analyze(station_id: str, displacements: list[dict]):
    return analyze_displacement(station_id, displacements)


@router.get("/geomagnetic-info")
async def geomagnetic_info():
    return get_geomagnetic_info()


@router.post("/geomagnetic-analyze")
async def geomagnetic_analyze(observations: list[dict]):
    return analyze_geomagnetic(observations)


@router.get("/traffic-info")
async def traffic_info(region: Optional[str] = None):
    return get_traffic_info_urls(region)


@router.get("/road-impact")
async def road_impact(intensity: float = Query(..., ge=0, le=7)):
    return estimate_road_impact(intensity)


from fastapi.responses import PlainTextResponse
from app.services.data_export import export_csv, export_geojson, export_kml


@router.get("/export/csv")
async def export_events_csv(
    region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None,
):
    from datetime import datetime as dt
    start_dt = dt.fromisoformat(start) if start else None
    end_dt = dt.fromisoformat(end) if end else None
    records = await db.get_events_as_records(region=region, start=start_dt, end=end_dt)
    return PlainTextResponse(content=export_csv(records), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=quakemind_events.csv"})


@router.get("/export/geojson")
async def export_events_geojson(
    region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None,
):
    from datetime import datetime as dt
    start_dt = dt.fromisoformat(start) if start else None
    end_dt = dt.fromisoformat(end) if end else None
    records = await db.get_events_as_records(region=region, start=start_dt, end=end_dt)
    return export_geojson(records)


@router.get("/export/kml")
async def export_events_kml(
    region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None,
):
    from datetime import datetime as dt
    start_dt = dt.fromisoformat(start) if start else None
    end_dt = dt.fromisoformat(end) if end else None
    records = await db.get_events_as_records(region=region, start=start_dt, end=end_dt)
    return PlainTextResponse(content=export_kml(records), media_type="application/vnd.google-earth.kml+xml",
                             headers={"Content-Disposition": "attachment; filename=quakemind_events.kml"})
