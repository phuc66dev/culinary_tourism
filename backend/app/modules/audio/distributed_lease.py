"""MongoDB-backed leases for the three GLOBAL Edge-TTS work slots.

Each slot is a single document, acquired by atomic compare-and-set. Heartbeats
prevent healthy work from being mistaken for a crashed worker. Tokens fence
stale workers after a slot is re-acquired by another process.

MongoDB replica set is already required by the project's transaction layer.
"""
import asyncio
from datetime import timedelta
from uuid import uuid4

from pymongo.errors import DuplicateKeyError

from app.core.database import get_db
from app.modules.audio.task_store import now

GLOBAL_AUDIO_SLOTS = 3
LEASE_SECONDS = 90
HEARTBEAT_SECONDS = 15
WAIT_SECONDS = 0.35


class AudioSlotLease:
    def __init__(self, token: str | None = None):
        self.token = token or uuid4().hex
        self.slot_id: str | None = None

    @staticmethod
    async def ensure_slots():
        collection = get_db()["audio_worker_slots"]
        for i in range(GLOBAL_AUDIO_SLOTS):
            try:
                await collection.update_one(
                    {"_id": f"slot-{i}"},
                    {"$setOnInsert": {"expires_at": now() - timedelta(seconds=1)}},
                    upsert=True,
                )
            except DuplicateKeyError:
                # Another API process created the exact same slot concurrently.
                pass

    async def acquire(self):
        """Wait for a global slot; cancellation interrupts the wait."""
        await self.ensure_slots()
        collection = get_db()["audio_worker_slots"]
        while True:
            current = now()
            expiry = current + timedelta(seconds=LEASE_SECONDS)
            for i in range(GLOBAL_AUDIO_SLOTS):
                slot = f"slot-{i}"
                result = await collection.update_one(
                    {"_id": slot, "expires_at": {"$lte": current}},
                    {"$set": {"token": self.token, "expires_at": expiry, "claimed_at": current}},
                )
                if result.modified_count:
                    self.slot_id = slot
                    return
            await asyncio.sleep(WAIT_SECONDS)

    async def refresh(self) -> bool:
        if self.slot_id is None:
            return False
        result = await get_db()["audio_worker_slots"].update_one(
            {"_id": self.slot_id, "token": self.token},
            {"$set": {"expires_at": now() + timedelta(seconds=LEASE_SECONDS)}},
        )
        return bool(result.matched_count)

    async def release(self):
        if self.slot_id is not None:
            await get_db()["audio_worker_slots"].update_one(
                {"_id": self.slot_id, "token": self.token},
                {"$set": {"expires_at": now() - timedelta(seconds=1)}, "$unset": {"token": ""}},
            )
            self.slot_id = None
