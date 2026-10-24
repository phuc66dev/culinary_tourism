"""
Router cho phân hệ Localization (`/api/v1/localizations/*`).
Phụ trách: Bảo
"""
from fastapi import APIRouter
from app.modules.localization.service import localization_service

router = APIRouter()


@router.post("/on-demand")
async def on_demand_localization(payload: dict):
    """Tier 1.5 Audio Fallback: Dịch + tạo TTS tức thì cho POI đang ở trạng thái fallback."""
    return await localization_service.generate_on_demand(
        poi_id=payload.get("poi_id", ""), lang=payload.get("lang", "en")
    )


@router.post("/prepare-hotset")
async def prepare_hotset(payload: dict):
    """Chuẩn bị trước dữ liệu bản dịch & audio cho tối đa 10 POI trong bán kính 1.5km."""
    return await localization_service.prepare_hotset(
        lat=payload.get("lat", 10.758),
        lng=payload.get("lng", 106.702),
        lang=payload.get("lang", "en"),
    )


@router.post("/warmup")
async def warmup_locale(payload: dict):
    """Khởi động trước (warmup) gói ngôn ngữ dưới nền khi người dùng chuyển ngôn ngữ."""
    return {"status": "warming_up", "lang": payload.get("lang", "en")}
