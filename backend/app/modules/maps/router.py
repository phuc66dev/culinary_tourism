"""Router cho phân hệ Maps (`/api/v1/maps/*`)."""
from fastapi import APIRouter, HTTPException, Query, Request

from app.core.cache import login_attempt_allowed
from app.modules.maps.service import maps_service

router = APIRouter()


@router.get("/offline-options")
async def get_offline_map_options():
    """Trả về thông tin gói bản đồ `.pmtiles` Quận 4 (dùng cho cả Startup Network Probe)."""
    return await maps_service.get_offline_options()


async def _check_lookup_limit(request: Request):
    ip = request.client.host if request.client else None
    if not await login_attempt_allowed("maps-geocode", ip, max_attempts=30, window_seconds=60):
        raise HTTPException(429, "Bạn đã tra cứu quá nhiều lần. Hãy thử lại sau.")


@router.get("/search-address")
async def search_address(request: Request, q: str = Query(min_length=3, max_length=400)):
    query = q.strip()
    if len(query) < 3:
        raise HTTPException(422, "Nhập ít nhất 3 ký tự để tìm địa chỉ")
    await _check_lookup_limit(request)
    return await maps_service.search_address(query)


@router.get("/reverse-geocode")
async def reverse_geocode(
    request: Request,
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
):
    await _check_lookup_limit(request)
    return await maps_service.reverse_geocode(lat, lng)
