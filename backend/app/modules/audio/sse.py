import asyncio
import json
from typing import AsyncIterator

from app.core.config import settings
from app.modules.audio.task_store import AudioTaskStore, audio_task_store


def _frame(event: str, payload: str) -> str:
    return f"event: {event}\ndata: {payload}\n\n"


async def audio_tasks_event_stream(
    request,
    store: AudioTaskStore = audio_task_store,
    interval: float | None = None,
) -> AsyncIterator[str]:
    interval = interval if interval is not None else float(settings.AUDIO_TASK_HEARTBEAT_SECONDS)
    changed = store.subscribe()
    last: str | None = None
    try:
        yield "retry: 3000\n\n"  # client tự kết nối lại sau 3s nếu rớt mạng
        while not await request.is_disconnected():
            # Clear BEFORE reading MongoDB; notifications arriving during/after the read
            # remain set, so a fast sequence of updates cannot be dropped.
            changed.clear()
            snapshot = json.dumps(await store.list(), ensure_ascii=False, default=str)
            if snapshot != last:
                yield _frame("tasks", snapshot)
                last = snapshot
            else:
                yield ": keepalive\n\n"
            try:
                await asyncio.wait_for(changed.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass
    finally:
        store.unsubscribe(changed)
