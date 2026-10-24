"""
LocalizationService — Xử lý dịch thuật & TTS theo yêu cầu (Tier 1.5) và chuẩn bị Hotset 1.5km.
Phụ trách: Bảo & Vũ
"""


class LocalizationService:
    async def generate_on_demand(self, poi_id: str, lang: str) -> dict:
        """
        TODO (Bảo / Vũ - Tier 1.5 Audio Fallback):
        - Dịch mô tả POI sang `lang` (Deep-Translator) + tổng hợp giọng đọc (Edge-TTS).
        - Lưu vào `poi_localizations` và trả về `audio_url` mới.
        - Áp dụng rate limit `ON_DEMAND_RATE_LIMIT` (30 req / 10 phút).
        """
        return {"poi_id": poi_id, "lang": lang, "audio_url": None, "is_fallback": False}

    async def prepare_hotset(self, lat: float, lng: float, lang: str) -> dict:
        """
        TODO (Bảo):
        - Lấy tối đa 10 POI gần nhất trong bán kính 1.5km (`HOTSET_MAX_POI_IDS = 10`).
        - Đảm bảo bản dịch và audio cho các POI ưu tiên quanh người dùng.
        """
        return {"lang": lang, "hotset_poi_ids": [], "ready": True}


localization_service = LocalizationService()
