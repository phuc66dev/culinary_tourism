"""Router cho phân hệ Runtime Observability (`/api/v1/runtime/*`)."""
from fastapi import APIRouter
from app.modules.runtime_observability.service import runtime_observability_service

router = APIRouter()


@router.post("/location")
async def ingest_public_location(payload: dict):
    """Ingest vị trí ẩn danh để phục vụ giám sát vận hành theo giờ."""
    return await runtime_observability_service.ingest_location(payload)
