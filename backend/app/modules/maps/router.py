"""Router cho phân hệ Maps (`/api/v1/maps/*`)."""
from fastapi import APIRouter
from app.modules.maps.service import maps_service

router = APIRouter()


@router.get("/offline-options")
async def get_offline_map_options():
    """Trả về thông tin gói bản đồ `.pmtiles` Quận 4 (dùng cho cả Startup Network Probe)."""
    return await maps_service.get_offline_options()
