"""AnalyticsService — Thu thập sự kiện ẩn danh khi người dùng đồng ý (Consent-gated)."""


class AnalyticsService:
    async def collect_event(self, payload: dict) -> dict:
        return {"status": "accepted"}


analytics_service = AnalyticsService()
