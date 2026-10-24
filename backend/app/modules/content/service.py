"""
Service xử lý nghiệp vụ POI, Delta Sync, 3-Tier Content Fallback và Activation Gate.
Phụ trách: Bảo (Public APIs) & Vũ (Admin CRUD / Activation Gate)
"""


class ContentService:
    async def load_all_pois(
        self,
        lang: str = "vi",
        updated_after: str | None = None,
        if_none_match: str | None = None,
    ) -> dict:
        """
        TODO (Bảo / Vũ):
        - Hỗ trợ full sync hoặc delta sync bằng `If-None-Match` (ETag) + `updated_after`.
        - Áp dụng 3-Tier Content Fallback:
          Tier 1: Ngôn ngữ yêu cầu (`lang`)
          Tier 2: English Fallback (`en`) -> đánh dấu `is_fallback = True`
          Tier 3: Nguyên bản tiếng Việt (`vi`) -> `audio_url = None`
        - Trả về: `items`, `dataset_version`, `sync_mode`, `removed_poi_ids`, `sync_cursor`.
        """
        return {
            "items": [],
            "dataset_version": "v1-skeleton",
            "sync_mode": "full",
            "removed_poi_ids": [],
            "sync_cursor": None,
        }

    async def get_nearby_pois(
        self, lat: float, lng: float, radius_m: int = 1500, lang: str = "vi"
    ) -> list[dict]:
        """
        TODO (Bảo):
        - Ưu tiên truy vấn `$geoNear` trên 2dsphere index.
        - Fallback sang tính khoảng cách Haversine in-memory nếu cần.
        """
        return []


content_service = ContentService()
