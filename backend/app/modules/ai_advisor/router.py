"""
Router cho phân hệ AI Advisor (`/api/v1/ai/*`).
Phụ trách: Phúc (Task 2.8 - 2.10)
"""
from fastapi import APIRouter
from app.modules.ai_advisor.schemas import EnhanceDescriptionRequest
from app.modules.ai_advisor.service import ai_advisor_service

router = APIRouter()


@router.get("/usage")
async def get_ai_usage():
    """Kiểm tra số lượt sử dụng AI còn lại trong ngày của Chủ quán."""
    return await ai_advisor_service.get_daily_usage(user_id="current_owner_skeleton")


@router.post("/enhance-description")
async def enhance_description(payload: EnhanceDescriptionRequest):
    """Sinh đoạn văn thuyết minh ẩm thực 200-300 từ bằng Gemini 2.5 Flash."""
    enhanced_text = await ai_advisor_service.enhance_poi_description(
        poi_name=payload.poi_name,
        keywords=payload.keywords,
        raw_notes=payload.raw_notes,
    )
    return {"enhanced_description": enhanced_text}
