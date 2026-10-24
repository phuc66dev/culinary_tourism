"""Router cho phân hệ Analytics (`/api/v1/analytics/*`)."""
from fastapi import APIRouter
from app.modules.analytics.service import analytics_service

router = APIRouter()


@router.post("/collect")
async def collect_analytics_event(payload: dict):
    """Ingest sự kiện phân tích ẩn danh (chỉ hoạt động khi user đã grant consent)."""
    return await analytics_service.collect_event(payload)
