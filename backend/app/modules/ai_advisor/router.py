"""
Router cho phân hệ AI Advisor (`/api/v1/ai/*`).
Phụ trách: Phúc (Task 2.8 - 2.10)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.rbac import require_permission
from app.modules.ai_advisor.schemas import EnhanceDescriptionRequest
from app.modules.ai_advisor.service import ai_advisor_service

router = APIRouter()


@router.get("/usage")
async def get_ai_usage(user: dict = Depends(require_permission("owner:access"))):
    """Kiểm tra số lượt sử dụng AI còn lại trong ngày của Chủ quán."""
    if not user.get("is_poi_owner_verified", False):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Hồ sơ chủ quán chưa được xác minh")
    return await ai_advisor_service.get_daily_usage(user_id=user["id"])


@router.post("/enhance-description")
async def enhance_description(
    payload: EnhanceDescriptionRequest,
    user: dict = Depends(require_permission("owner:access")),
):
    """Sinh đoạn văn thuyết minh ẩm thực 200-300 từ bằng Gemini 2.5 Flash."""
    enhanced_text = await ai_advisor_service.enhance_poi_description(payload, user)
    usage = await ai_advisor_service.get_daily_usage(user["id"])
    return {"enhanced_description": enhanced_text, "usage": usage}
