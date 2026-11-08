"""Gemini-powered description assistance with atomic per-owner daily quotas."""
import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.database import get_db
from app.modules.ai_advisor.schemas import EnhanceDescriptionRequest
from app.modules.owner.service import _owned_poi, owner_object_id

logger = logging.getLogger("quan4.ai_advisor")


class AIAdvisorService:
    def _day(self) -> str:
        return datetime.now(timezone.utc).date().isoformat()

    async def get_daily_usage(self, user_id: str) -> dict:
        if not user_id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chưa đăng nhập")
        used = await get_db()["ai_usage_limits"].find_one(
            {"user_id": user_id, "date": self._day()}, {"used_today": 1}
        )
        used_today = int((used or {}).get("used_today", 0))
        limit = settings.OWNER_DAILY_LIMIT
        return {"used_today": used_today, "daily_limit": limit, "remaining": max(0, limit - used_today)}

    async def _claim_slot(self, user_id: str, day: str) -> None:
        collection = get_db()["ai_usage_limits"]
        try:
            await collection.update_one(
                {"user_id": user_id, "date": day},
                {"$setOnInsert": {"used_today": 0, "created_at": datetime.now(timezone.utc)}},
                upsert=True,
            )
        except DuplicateKeyError:
            # Another request initialized this owner's record concurrently.
            pass
        claimed = await collection.find_one_and_update(
            {"user_id": user_id, "date": day, "used_today": {"$lt": settings.OWNER_DAILY_LIMIT}},
            {"$inc": {"used_today": 1}, "$set": {"updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
        if not claimed:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                "Bạn đã dùng hết lượt hỗ trợ AI hôm nay")

    async def _release_slot(self, user_id: str, day: str) -> None:
        await get_db()["ai_usage_limits"].update_one(
            {"user_id": user_id, "date": day, "used_today": {"$gt": 0}},
            {"$inc": {"used_today": -1}, "$set": {"updated_at": datetime.now(timezone.utc)}},
        )

    async def enhance_poi_description(self, payload: EnhanceDescriptionRequest, user: dict) -> str:
        owner_id = owner_object_id(user)
        if not user.get("is_poi_owner_verified", False):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Hồ sơ chủ quán chưa được xác minh")
        poi = await _owned_poi(payload.poi_id, user)
        if poi.get("name") != payload.poi_name:
            # The POI name is authoritative; callers cannot use the advisor to impersonate another venue.
            poi_name = str(poi.get("name") or "")
        else:
            poi_name = payload.poi_name
        if not settings.GEMINI_API_KEY:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI Advisor chưa được cấu hình")

        user_id = str(owner_id)
        day = self._day()
        await self._claim_slot(user_id, day)
        notes = payload.raw_notes.strip()
        keywords = ", ".join(item.strip() for item in payload.keywords if item.strip())
        prompt = (
            "Bạn là biên tập viên thuyết minh du lịch ẩm thực tại Quận 4, viết bằng tiếng Việt tự nhiên. "
            "Hãy tạo một đoạn giới thiệu dài 200-300 từ. Chỉ dùng dữ kiện có trong tên quán, từ khóa và ghi chú; "
            "không bịa lịch sử, địa chỉ, giá, giờ mở cửa, nguyên liệu hay giải thưởng. Nếu thiếu dữ kiện, "
            "hãy mô tả khái quát, không khẳng định điều chưa biết. Văn phong ấm áp, hấp dẫn, phù hợp khách du lịch.\n\n"
            f"Tên quán: {poi_name}\nTừ khóa: {keywords or '(không có)'}\nGhi chú của chủ quán: {notes or '(không có)'}"
        )
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            for attempt in range(2):
                response = await model.generate_content_async(
                    prompt,
                    generation_config={"temperature": 0.35, "max_output_tokens": 900},
                )
                text = (getattr(response, "text", None) or "").strip()
                word_count = len(text.split())
                if 200 <= word_count <= 300:
                    return text
                if attempt == 0:
                    prompt += "\nHãy viết lại trong khoảng 220-260 từ tiếng Việt, tính theo các từ ngăn cách bằng khoảng trắng."
            raise RuntimeError("Gemini response is outside the required word range")
        except Exception as exc:
            await self._release_slot(user_id, day)
            logger.warning("Gemini request failed (%s)", type(exc).__name__)
            raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                                "Không tạo được nội dung lúc này. Vui lòng thử lại sau.") from exc


ai_advisor_service = AIAdvisorService()
