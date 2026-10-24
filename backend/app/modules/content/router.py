"""
Router cho phân hệ Content (`/api/v1/poi/*`).
Phụ trách: Bảo
"""
from typing import Optional
from fastapi import APIRouter, Header, Query
from app.modules.content.service import content_service

router = APIRouter()


@router.get("/load-all")
async def load_all_pois(
    lang: str = Query("vi", description="Mã ngôn ngữ: vi, en, zh, ja, ko"),
    updated_after: Optional[str] = Query(None, description="ISO timestamp cho Delta Sync"),
    if_none_match: Optional[str] = Header(None),
):
    """API tải danh sách POI (hỗ trợ ETag, Delta Sync & 3-Tier Fallback)."""
    return await content_service.load_all_pois(
        lang=lang, updated_after=updated_after, if_none_match=if_none_match
    )


@router.get("/nearby")
async def get_nearby_pois(
    lat: float = Query(..., description="Vĩ độ người dùng"),
    lng: float = Query(..., description="Kinh độ người dùng"),
    radius_m: int = Query(1500, description="Bán kính tìm kiếm (mét)"),
    lang: str = Query("vi"),
):
    """API tìm các quán ăn lân cận bằng truy vấn không gian ($geoNear)."""
    items = await content_service.get_nearby_pois(lat=lat, lng=lng, radius_m=radius_m, lang=lang)
    return {"items": items}
