from datetime import datetime, timezone
import re
from typing import Optional

from bson import ObjectId
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from app.core.config import settings
from app.core.database import get_db, mongo_transaction
from app.modules.admin.audit import write_audit_event

STATUSES = ("pending", "approved", "rejected")
MAX_NOTE_LENGTH = 500


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _object_id(value, label: str = "registration ID") -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    if not isinstance(value, str) or not ObjectId.is_valid(value):
        raise HTTPException(400, f"Invalid {label}")
    return ObjectId(value)


def _iso(value) -> Optional[str]:
    if not isinstance(value, datetime):
        return None
    # PyMongo often returns naive datetimes even when the original write was UTC.
    # Always expose an explicit UTC offset to JavaScript clients.
    utc_value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return utc_value.isoformat()


def _serialize(doc: dict, email: Optional[str] = None) -> dict:
    return {
        "id": str(doc["_id"]),
        "user_id": str(doc.get("user_id", "")),
        "email": email,
        "full_name": doc.get("full_name"),
        "phone": doc.get("phone"),
        "poi_name": doc.get("poi_name"),
        "poi_address": doc.get("poi_address"),
        "storefront_image_url": doc.get("storefront_image_url"),
        "status": doc.get("status"),
        "admin_note": doc.get("admin_note"),
        "created_at": _iso(doc.get("created_at")),
        "reviewed_at": _iso(doc.get("reviewed_at")),
        "cccd_available": bool(doc.get("cccd_encrypted") or doc.get("encrypted_cccd")),
    }


async def list_registrations(status: Optional[str] = None, q: Optional[str] = None,
                             limit: int = 100, skip: int = 0) -> dict:
    """Search in Mongo BEFORE pagination, including users' emails (not just first N docs)."""
    if status is not None and status not in STATUSES:
        raise HTTPException(422, "status must be pending, approved or rejected")
    db = get_db()
    query: dict = {"status": status} if status else {}
    if q and q.strip():
        pattern = {"$regex": re.escape(q.strip()), "$options": "i"}
        email_ids = [u["_id"] async for u in db["users"].find({"email": pattern}, {"_id": 1})]
        query["$or"] = [
            {field: pattern} for field in ("full_name", "poi_name", "phone")
        ] + [{"user_id": {"$in": email_ids + [str(uid) for uid in email_ids]}}]
    total = await db["poi_owner_registrations"].count_documents(query)
    docs = [d async for d in db["poi_owner_registrations"].find(query)
            .sort("created_at", -1).skip(skip).limit(limit)]
    user_ids = [_object_id(d["user_id"], "user ID") for d in docs
                if d.get("user_id") and ObjectId.is_valid(str(d["user_id"]))]
    emails = {
        u["_id"]: u.get("email")
        async for u in db["users"].find({"_id": {"$in": user_ids}}, {"email": 1})
    }
    items = []
    for d in docs:
        uid = d.get("user_id")
        email = emails.get(ObjectId(uid) if isinstance(uid, str) and ObjectId.is_valid(uid) else uid)
        items.append(_serialize(d, email))
    counts = {s: await db["poi_owner_registrations"].count_documents({"status": s}) for s in STATUSES}
    return {"items": items, "counts": counts, "total": total, "limit": limit, "skip": skip}


def _fernet() -> Fernet:
    if not settings.FERNET_KEY:
        raise HTTPException(503, "FERNET_KEY not configured")
    try:
        return Fernet(settings.FERNET_KEY.encode())
    except ValueError as exc:
        raise HTTPException(503, "FERNET_KEY is invalid") from exc


async def reveal_cccd(reg_id: str, user: dict, ip: Optional[str]) -> dict:
    """Giải mã CCCD theo yêu cầu tường minh của Admin; luôn ghi audit log."""
    doc = await get_db()["poi_owner_registrations"].find_one({"_id": _object_id(reg_id)})
    if not doc:
        raise HTTPException(404, "Registration not found")
    cipher = doc.get("cccd_encrypted") or doc.get("encrypted_cccd")
    if not cipher:
        raise HTTPException(404, "Encrypted CCCD not available")
    fernet = _fernet()
    try:
        # Backwards-compatible ciphertext storage: `v1:<Fernet token>` in text/bytes.
        token = cipher.decode("utf-8") if isinstance(cipher, bytes) else str(cipher)
        if token.startswith("v1:"):
            token = token[3:]
        elif ":" in token:  # Không tự ý giải mã ciphertext thuộc phiên bản chưa hỗ trợ.
            raise ValueError("Unsupported CCCD cipher version")
        value = fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeError) as exc:
        raise HTTPException(422, "Cannot decrypt CCCD") from exc
    # Audit bắt buộc thành công trước khi cho phép trả PII; không lưu số CCCD vào log.
    await write_audit_event(user.get("id"), "owner.cccd_reveal", f"registration:{reg_id}", ip)
    return {"cccd_number": value}


async def review_registration(reg_id: str, action: str, note: Optional[str], user: dict, ip: Optional[str]) -> dict:
    if action not in ("approve", "reject"):
        raise HTTPException(422, "action must be approve or reject")
    note = (note or "").strip()
    if action == "reject" and not note:
        raise HTTPException(422, "Rejection reason required")
    if len(note) > MAX_NOTE_LENGTH:
        raise HTTPException(422, f"admin_note tối đa {MAX_NOTE_LENGTH} ký tự")

    db = get_db()
    rid = _object_id(reg_id)
    new_status = "approved" if action == "approve" else "rejected"
    from app.modules.admin.audit import write_audit_event
    async with mongo_transaction() as tx:
        reg = await db["poi_owner_registrations"].find_one({"_id": rid}, session=tx)
        if not reg:
            raise HTTPException(404, "Registration not found")
        if reg.get("status") != "pending":
            raise HTTPException(409, "Registration already reviewed")
        uid = reg.get("user_id")
        if not uid or not ObjectId.is_valid(str(uid)):
            raise HTTPException(409, "Invalid owner user_id")
        uid = ObjectId(str(uid))
        if not await db["users"].find_one({"_id": uid}, {"_id": 1}, session=tx):
            raise HTTPException(409, "Owner account not found")
        res = await db["poi_owner_registrations"].update_one(
            {"_id": rid, "status": "pending"},
            {"$set": {"status": new_status, "admin_note": note or None,
                      "reviewed_by": user.get("id"), "reviewed_at": _now()}}, session=tx,
        )
        if not res.modified_count:
            raise HTTPException(409, "Registration already reviewed")
        if action == "approve":
            await db["users"].update_one({"_id": uid}, {"$set": {
                "is_poi_owner_verified": True, "updated_at": _now()}}, session=tx)
        await db["owner_notifications"].insert_one({
            "user_id": uid, "type": "registration_review", "registration_id": rid,
            "title": "Kết quả duyệt hồ sơ",
            "message": "Hồ sơ đã được duyệt" if action == "approve" else f"Hồ sơ bị từ chối: {note}",
            "admin_note": note or None, "is_read": False, "created_at": _now(),
        }, session=tx)
        await write_audit_event(user.get("id"), f"owner.registration_{action}",
            f"registration:{reg_id}", ip,
            {"status": new_status, "poi_name": reg.get("poi_name"), "has_note": bool(note)}, session=tx)
    return {"id": reg_id, "status": new_status}
