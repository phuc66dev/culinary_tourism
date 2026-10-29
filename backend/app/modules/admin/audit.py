from datetime import datetime, timezone
import hashlib
import re
from typing import Any

from bson import ObjectId
from fastapi import HTTPException

from app.core.config import settings
from app.core.database import get_db

_SENSITIVE_KEY = re.compile(
    r"(password|secret|token|authorization|cookie|cccd|identity|card_number|"
    r"encrypted|fernet|phone|email|credential)", re.IGNORECASE,
)
_MAX_DEPTH = 4
_MAX_ITEMS = 40


def _redact(value: Any, depth: int = 0) -> Any:
    """Whitelist JSON-like scalar output, bounded to prevent accidental PII dumps."""
    if depth >= _MAX_DEPTH:
        return "[truncated]"
    if isinstance(value, dict):
        return {
            str(k)[:80]: ("[redacted]" if _SENSITIVE_KEY.search(str(k)) else _redact(v, depth + 1))
            for k, v in list(value.items())[:_MAX_ITEMS]
        }
    if isinstance(value, (list, tuple)):
        return [_redact(x, depth + 1) for x in value[:_MAX_ITEMS]]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    if isinstance(value, str):
        return value[:500]
    return str(value)[:160]


def fingerprint_login(email: str) -> str:
    """Correlate failed login attempts without persisting a plaintext email."""
    key = settings.JWT_SECRET.encode("utf-8")
    from hmac import new
    return new(key, email.strip().casefold().encode("utf-8"), hashlib.sha256).hexdigest()[:24]


async def write_audit_event(
    user_id: str | None, action: str, resource: str, ip: str | None = None,
    details: dict | None = None, *, session=None,
) -> None:
    db = get_db()
    actor = None
    if user_id and ObjectId.is_valid(str(user_id)):
        # Snapshot actor identity at event time. Historical logs stay readable
        # even if the account is subsequently renamed or deleted.
        actor = await db["users"].find_one(
            {"_id": ObjectId(str(user_id))},
            {"email": 1, "full_name": 1, "role": 1}, session=session,
        )
    # Snapshot the affected entity as well as the actor. Once an account/POI is
    # removed or renamed, the audit timeline must still identify the target.
    # Target email is intentionally a top-level restricted audit field, not a
    # generic details value (which is redacted to prevent accidental PII leaks).
    target_name = None
    target_email = None
    kind, _, identifier = resource.partition(":")
    if kind in {"user", "poi"} and ObjectId.is_valid(identifier):
        collection = "users" if kind == "user" else "poi"
        projection = {"full_name": 1, "email": 1} if kind == "user" else {"name": 1}
        target = await db[collection].find_one(
            {"_id": ObjectId(identifier)}, projection, session=session,
        )
        if target:
            target_name = target.get("full_name") if kind == "user" else target.get("name")
            if kind == "user":
                target_email = target.get("email")
    if not target_name and kind in {"registration", "submission", "audio_task"} and ObjectId.is_valid(identifier):
        related_collection = {
            "registration": "poi_owner_registrations",
            "submission": "poi_submissions",
            "audio_task": "audio_tasks",
        }[kind]
        related = await db[related_collection].find_one(
            {"_id": ObjectId(identifier)}, session=session,
        )
        if related:
            target_name = related.get("poi_name")
            poi_id = related.get("poi_id")
            if not target_name and poi_id and ObjectId.is_valid(str(poi_id)):
                related_poi = await db["poi"].find_one(
                    {"_id": ObjectId(str(poi_id))}, {"name": 1}, session=session,
                )
                target_name = (related_poi or {}).get("name")
    if not target_name:
        target_name = (details or {}).get("poi_name") or (details or {}).get("target_name")
    await db["audit_logs"].insert_one({
        "user_id": str(user_id) if user_id else None,
        "actor_name": (actor or {}).get("full_name"),
        "actor_email": (actor or {}).get("email"),
        "actor_role": (actor or {}).get("role"),
        "target_name": str(target_name)[:160] if target_name else None,
        "target_email": str(target_email)[:254] if target_email else None,
        "action": action[:100],
        "resource": resource[:200],
        "ip": (ip or "")[:64] or None,
        "details": _redact(details or {}),
        "created_at": datetime.now(timezone.utc),
    }, session=session)


def _serialize(doc: dict) -> dict:
    stamp = doc.get("created_at")
    return {
        "id": str(doc["_id"]),
        "user_id": doc.get("user_id"),
        "actor_name": doc.get("actor_name"),
        "actor_email": doc.get("actor_email"),
        "actor_role": doc.get("actor_role"),
        "target_name": doc.get("target_name"),
        "target_email": doc.get("target_email"),
        "action": doc.get("action"),
        "resource": doc.get("resource"),
        "ip": doc.get("ip"),
        "details": _redact(doc.get("details") or {}),
        "created_at": _utc(stamp).isoformat() if isinstance(stamp, datetime) else None,
    }


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


async def list_audit_events(
    q: str | None = None,
    action: str | None = None,
    user_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int = 50,
    skip: int = 0,
    *, resource: str | None = None,
) -> dict:
    from_time, to_time = _utc(from_time), _utc(to_time)
    if from_time and to_time and from_time > to_time:
        raise HTTPException(422, "from_time must be before to_time")
    query: dict = {}
    if q and q.strip():
        needle = {"$regex": re.escape(q.strip()), "$options": "i"}
        query["$or"] = [
            {"action": needle}, {"resource": needle}, {"details.poi_name": needle},
            {"actor_name": needle}, {"actor_email": needle},
            {"target_name": needle}, {"target_email": needle},
        ]
    if action:
        query["action"] = action
    if user_id:
        query["user_id"] = user_id
    if resource:
        query["resource"] = resource.strip()
    if from_time or to_time:
        query["created_at"] = {}
        if from_time:
            query["created_at"]["$gte"] = from_time
        if to_time:
            query["created_at"]["$lte"] = to_time
    db = get_db()
    total = await db["audit_logs"].count_documents(query)
    cursor = db["audit_logs"].find(query).sort([("created_at", -1), ("_id", -1)]).skip(skip).limit(limit)
    return {
        "items": [_serialize(doc) async for doc in cursor],
        "total": total,
        "limit": limit,
        "skip": skip,
    }
