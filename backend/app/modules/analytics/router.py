"""Router cho phân hệ Analytics (`/api/v1/analytics/*`)."""
from fastapi import APIRouter, HTTPException, Request

from app.core.cache import login_attempt_allowed
from app.modules.analytics.schemas import AnalyticsBatch
from app.modules.analytics.service import analytics_service

router = APIRouter()


@router.post("/collect")
async def collect_analytics_event(payload: AnalyticsBatch, request: Request):
    """Ingest sự kiện phân tích ẩn danh (chỉ hoạt động khi user đã grant consent)."""
    ip = request.client.host if request.client else None
    if not await login_attempt_allowed("poi-analytics", ip, max_attempts=120, window_seconds=60):
        raise HTTPException(status_code=429, detail="Thử gửi lại sự kiện sau.")
    return await analytics_service.collect_event(payload)
