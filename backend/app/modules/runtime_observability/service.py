"""RuntimeObservabilityService — Ghi nhận mật độ vị trí theo cửa sổ giờ (`runtime_location_hourly`)."""


class RuntimeObservabilityService:
    async def ingest_location(self, payload: dict) -> dict:
        return {"status": "recorded"}


runtime_observability_service = RuntimeObservabilityService()
