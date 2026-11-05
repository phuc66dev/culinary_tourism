import asyncio
from datetime import datetime, timedelta, timezone
from typing import Iterable

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError

from app.core.database import get_db, mongo_transaction

ACTIVE_STATUSES = ("queued", "running", "paused")
FINISHED_STATUSES = ("completed", "failed", "cancelled")


def now() -> datetime:
    return datetime.now(timezone.utc)


def oid(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def _timestamp_iso(value: datetime) -> str:
    """PyMongo decodes UTC dates as naive by default; never send them to JS as local time."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def serialize(doc):
    if not doc:
        return None
    out = {
        k: str(v) if isinstance(v, ObjectId) else _timestamp_iso(v) if isinstance(v, datetime) else v
        for k, v in doc.items()
        if k != "_id"
    }
    out["id"] = str(doc["_id"])
    return out


class AudioTaskStore:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Event] = set()

    @property
    def collection(self):
        return get_db()["audio_tasks"]

    # ---- Pub/sub nội bộ cho SSE: có thay đổi là đẩy ngay, không phải chờ chu kỳ poll ----
    def subscribe(self) -> asyncio.Event:
        event = asyncio.Event()
        self._subscribers.add(event)
        return event

    def unsubscribe(self, event: asyncio.Event) -> None:
        self._subscribers.discard(event)

    def _notify(self) -> None:
        for event in list(self._subscribers):
            event.set()

    # ---- CRUD ----
    async def create(self, poi_id: str, poi_name: str, languages: list[str], *,
                     session=None, notify: bool = True) -> str:
        t = now()
        result = await self.collection.insert_one(
            {
                "poi_id": poi_id,
                "poi_name": poi_name,
                "languages": languages,
                "done": 0,
                "total": len(languages),
                "current_language": None,
                "cache_hits": 0,
                "status": "queued",
                "error": None,
                "created_at": t,
                "updated_at": t,
            }, session=session,
        )
        if notify:
            self._notify()
        return str(result.inserted_id)

    async def get(self, id):
        key = oid(id)
        return await self.collection.find_one({"_id": key}) if key else None

    async def update(self, id, **fields) -> None:
        key = oid(id)
        if not key:
            return
        await self.collection.update_one({"_id": key}, {"$set": {**fields, "updated_at": now()}})
        self._notify()

    async def update_if(self, id, statuses: Iterable[str], inc: dict | None = None,
                        lease_token: str | None = None,
                        unset: tuple[str, ...] = (), **fields) -> bool:
        """Chỉ ghi khi trạng thái hiện tại nằm trong `statuses`. Trả về True nếu đã ghi."""
        key = oid(id)
        if not key:
            return False
        operation: dict = {"$set": {**fields, "updated_at": now()}}
        if inc:
            operation["$inc"] = inc
        if unset:
            operation["$unset"] = {field: "" for field in unset}
        query = {"_id": key, "status": {"$in": list(statuses)}}
        if lease_token is not None:
            query["lease_token"] = lease_token
            query["lease_until"] = {"$gt": now()}
        result = await self.collection.update_one(query, operation)
        applied = result.matched_count > 0
        if applied:
            self._notify()
        return applied

    async def find_active_for_poi(self, poi_id: str):
        return await self.collection.find_one({"poi_id": poi_id, "status": {"$in": list(ACTIVE_STATUSES)}})

    async def list(self, limit: int = 50):
        return [serialize(t) async for t in self.collection.find().sort("created_at", -1).limit(limit)]

    async def purge_finished(self, retention_days: int) -> int:
        """Dọn tác vụ đã kết thúc quá `retention_days` ngày (AUDIO_TASK_RETENTION_DAYS)."""
        cutoff = now() - timedelta(days=retention_days)
        from app.modules.admin.audit import write_audit_event
        # Retention deletion is a sensitive system mutation, audit it in the same
        # transaction so a failed audit cannot silently purge task history.
        async with mongo_transaction() as tx:
            result = await self.collection.delete_many(
                {"status": {"$in": list(FINISHED_STATUSES)}, "updated_at": {"$lt": cutoff}},
                session=tx,
            )
            if result.deleted_count:
                await write_audit_event(None, "audio.task_purged", "audio_tasks:retention",
                                        details={"deleted_count": result.deleted_count,
                                                 "retention_days": retention_days}, session=tx)
        return result.deleted_count


audio_task_store = AudioTaskStore()
