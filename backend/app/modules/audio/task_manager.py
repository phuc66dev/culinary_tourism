"""
AudioTaskManager — Quản lý hàng đợi sinh audio bất đồng bộ với Semaphore(3) & Heartbeat.
Phụ trách: Vũ (Task 3.8, Task 3.9)
"""
import asyncio
from app.core.config import settings


class AudioTaskManager:
    def __init__(self) -> None:
        self.semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_TTS)

    async def enqueue_poi_audio_task(self, poi_id: str, languages: list[str] | None = None) -> str:
        """
        TODO (Vũ - Task 3.8):
        - Tạo bản ghi trong collection `audio_tasks` (trạng thái `queued`).
        - Chạy tiến trình nền với `asyncio.Semaphore(3)`.
        - Hỗ trợ Pause / Resume / Cancel và phát sự kiện tiến độ qua SSE.
        """
        return "task_id_skeleton"


audio_task_manager = AudioTaskManager()
