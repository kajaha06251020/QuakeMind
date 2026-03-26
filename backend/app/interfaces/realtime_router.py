"""リアルタイム評価 API ルーター (Phase C4)"""
from fastapi import APIRouter, Query
from app.usecases.shakemap import compute_shakemap
from app.usecases.tsunami_arrival import estimate_tsunami_arrival
from app.usecases.damage_estimation import estimate_damage

router = APIRouter(prefix="/realtime", tags=["realtime-assessment"])


@router.get("/shakemap")
async def get_shakemap(
    lat: float = Query(...), lon: float = Query(...),
    depth_km: float = Query(default=10.0), magnitude: float = Query(...),
    grid_spacing_deg: float = Query(default=0.2), grid_radius_deg: float = Query(default=3.0),
):
    return compute_shakemap(lat, lon, depth_km, magnitude, grid_spacing_deg, grid_radius_deg)


@router.get("/tsunami-arrival")
async def get_tsunami_arrival(
    lat: float = Query(...), lon: float = Query(...),
    depth_km: float = Query(default=10.0), magnitude: float = Query(...),
):
    return estimate_tsunami_arrival(lat, lon, depth_km, magnitude)


@router.get("/damage-estimate")
async def get_damage_estimate(
    lat: float = Query(...), lon: float = Query(...),
    depth_km: float = Query(default=10.0), magnitude: float = Query(...),
):
    return estimate_damage(lat, lon, depth_km, magnitude)
