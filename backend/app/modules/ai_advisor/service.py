"""
AIAdvisorService — Tích hợp Google Gemini 2.5 Flash & Quản lý hạn mức 10 lượt/ngày.
Phụ trách: Phúc (Task 2.8, Task 2.9)
"""
from app.core.config import settings


class AIAdvisorService:
    async def get_daily_usage(self, user_id: str) -> dict:
        """
        TODO (Phúc - Task 2.9):
        - Đọc collection `ai_usage_limits` theo `{user_id, date}`.
        - Hạn mức mặc định: `settings.OWNER_DAILY_LIMIT` (10 lượt/ngày).
        """
        return {
            "used_today": 0,
            "daily_limit": settings.OWNER_DAILY_LIMIT,
            "remaining": settings.OWNER_DAILY_LIMIT,
        }

    async def enhance_poi_description(self, poi_name: str, keywords: list[str], raw_notes: str) -> str:
        """
        TODO (Phúc - Task 2.8):
        - Gọi SDK Gemini 2.5 Flash với System Prompt:
          "Không được bịa đặt sự thật, sử dụng tính từ gợi cảm giác ngon miệng,
           văn phong du lịch ấm áp, độ dài 200-300 từ."
        """
        return f"[AI Skeleton] Mô tả gợi ý cho quán {poi_name} với từ khóa: {', '.join(keywords)}."


ai_advisor_service = AIAdvisorService()
