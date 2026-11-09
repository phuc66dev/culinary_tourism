from datetime import datetime, timedelta, timezone
import re
from typing import Optional

from bson import ObjectId
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from app.core.config import settings
from app.core.database import get_db, mongo_transaction
from app.modules.admin.audit import write_audit_event
from app.modules.admin.poi_management import bump_dataset, insert_poi, vietnamese_search_regex
from app.modules.admin.schemas import POICreateRequest, POILocation, RegistrationPOIDraft
from app.modules.owner.service import purge_expired_registration_pii

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


def _pii_expired(doc: dict) -> bool:
    expires = doc.get("cccd_expires_at")
    if not isinstance(expires, datetime):
        created = doc.get("created_at")
        if not isinstance(created, datetime):
            return False
        created = created.replace(tzinfo=timezone.utc) if created.tzinfo is None else created.astimezone(timezone.utc)
        expires = created + timedelta(days=settings.PII_RETENTION_DAYS)
    expires = expires.replace(tzinfo=timezone.utc) if expires.tzinfo is None else expires.astimezone(timezone.utc)
    return expires <= datetime.now(timezone.utc)


def _serialize(doc: dict, email: Optional[str] = None) -> dict:
    return {
        "id": str(doc["_id"]),
        "user_id": str(doc.get("user_id", "")),
        "email": email,
        "full_name": doc.get("full_name"),
        "phone": doc.get("phone"),
        "poi_name": doc.get("poi_name"),
        "poi_address": doc.get("poi_address"),
        "poi_location": doc.get("poi_location"),
        "storefront_image_url": doc.get("storefront_image_url"),
        "status": doc.get("status"),
        "linked_poi_id": str(doc["linked_poi_id"]) if doc.get("linked_poi_id") else None,
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
    await purge_expired_registration_pii()
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
    if _pii_expired(doc):
        await get_db()["poi_owner_registrations"].update_one(
            {"_id": doc["_id"]},
            {"$unset": {"cccd_encrypted": "", "encrypted_cccd": ""},
             "$set": {"pii_redacted_at": datetime.now(timezone.utc)}},
        )
        raise HTTPException(404, "CCCD đã hết thời hạn lưu trữ")
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


def _poi_pattern(value: str, *, exact: bool = False) -> dict:
    pattern = r"\s+".join(vietnamese_search_regex(word) for word in value.split())
    if exact:
        pattern = r"^\s*" + pattern + r"\s*$"
    return {"$regex": pattern, "$options": "i"}


def _registration_poi_identity(reg: dict) -> dict:
    return {
        "name": _poi_pattern(reg.get("poi_name") or "", exact=True),
        "address": _poi_pattern(reg.get("poi_address") or "", exact=True),
    }


async def search_registration_pois(reg_id: str, name: str, address: str) -> dict:
    db = get_db()
    reg = await db["poi_owner_registrations"].find_one({"_id": _object_id(reg_id)},
        {"user_id": 1, "poi_name": 1, "poi_address": 1},)
    if not reg:
        raise HTTPException(404, "Không tìm thấy hồ sơ")
    filters = [{field: _poi_pattern(term)} for field, term in (
        ("name", name), ("address", address)
    ) if term.strip()]
    if not filters:
        raise HTTPException(422, "Nhập tên hoặc địa chỉ để tìm quán")
    query = {"$and": filters}
    projection = {"name": 1, "address": 1, "owner_id": 1, "is_active": 1}
    docs = [doc async for doc in db["poi"].find(query, projection).sort([("name", 1), ("_id", 1)]).limit(31)]
    owner = str(reg.get("user_id"))
    exact_match = await db["poi"].find_one(_registration_poi_identity(reg), {"_id": 1})
    return {
        "has_exact_match": exact_match is not None,
        "items": [{
            "id": str(doc["_id"]), "name": doc.get("name"), "address": doc.get("address"),
            "is_active": bool(doc.get("is_active")),
            "can_link": doc.get("owner_id") is None or str(doc["owner_id"]) == owner,
        } for doc in docs[:30]],
        "has_more": len(docs) > 30,
    }


async def _publish_pinned_registration(reg, uid, user, ip, *, session) -> ObjectId:
    db = get_db()
    permissions = set(user.get("permissions", []))
    if "poi:toggle" not in permissions:
        raise HTTPException(403, "Thiếu quyền công khai quán (poi:toggle)")

    name = (reg.get("poi_name") or "").strip()
    address = (reg.get("poi_address") or "").strip()
    if not name or len(name) > 180 or not address or len(address) > 400:
        raise HTTPException(422, "Tên hoặc địa chỉ trong hồ sơ không hợp lệ")
    matches = await db["poi"].find(
        _registration_poi_identity(reg), {"_id": 1}, session=session,
    ).to_list(length=2)
    if len(matches) > 1:
        raise HTTPException(409, "Có nhiều quán trùng tên và địa chỉ. Hãy xử lý bản ghi trùng trước khi duyệt.")

    permission = "poi:update" if matches else "poi:create"
    if permission not in permissions:
        raise HTTPException(403, f"Bạn không có quyền thực hiện thao tác này ({permission})")
    if matches:
        pid = matches[0]["_id"]
        linked = await db["poi"].update_one(
            {"_id": pid, "$or": [{"owner_id": None}, {"owner_id": {"$in": [uid, str(uid)]}}]},
            {"$set": {"owner_id": uid, "location": reg["poi_location"],
                      "is_active": True, "updated_at": _now()}, "$inc": {"revision": 1}},
            session=session,
        )
        if not linked.matched_count:
            raise HTTPException(409, "Quán đã được gắn cho một chủ sở hữu khác")
        await bump_dataset(session=session)
        return pid

    image = (reg.get("storefront_image_url") or "").strip()
    payload = POICreateRequest(
        name=name,
        address=address,
        ward=reg.get("poi_ward") or "Chưa xác định",
        location=reg["poi_location"],
        original_description=f"{name} — {address}",
        images=[image] if 0 < len(image) <= 2048 else [],
    )
    return await insert_poi(payload, user, ip, session=session, owner_id=uid, publish_on_approval=True)


async def review_registration(
    reg_id: str, action: str, note: Optional[str], user: dict, ip: Optional[str],
    poi_id: Optional[str] = None, draft: RegistrationPOIDraft | None = None,
    *, poi_location: POILocation | None = None,
) -> dict:
    if action not in ("approve", "reject"):
        raise HTTPException(422, "action must be approve or reject")
    note = (note or "").strip()
    if action == "reject" and (not note or any(value is not None for value in (poi_id, draft, poi_location))):
        raise HTTPException(422, "Từ chối hồ sơ cần lý do và không kèm quán")
    if len(note) > MAX_NOTE_LENGTH:
        raise HTTPException(422, f"admin_note tối đa {MAX_NOTE_LENGTH} ký tự")

    db = get_db()
    rid = _object_id(reg_id)
    new_status = "approved" if action == "approve" else "rejected"
    linked_poi_id = None
    async with mongo_transaction() as tx:
        reg = await db["poi_owner_registrations"].find_one({"_id": rid}, session=tx)
        if not reg:
            raise HTTPException(404, "Registration not found")
        previous_status = reg.get("status")
        repairing = previous_status == "approved" and action == "approve" and not reg.get("linked_poi_id")
        if previous_status != "pending" and not repairing:
            raise HTTPException(409, "Hồ sơ đã được xử lý")
        uid = reg.get("user_id")
        if not uid or not ObjectId.is_valid(str(uid)):
            raise HTTPException(409, "Invalid owner user_id")
        uid = ObjectId(str(uid))
        if not await db["users"].find_one({"_id": uid, "role": "poi_owner"}, {"_id": 1}, session=tx):
            raise HTTPException(409, "Owner account not found")

        stamp = _now()
        updates = {}
        if not repairing:
            updates.update(status=new_status, admin_note=note or None,
                           reviewed_by=user.get("id"), reviewed_at=stamp)
        if poi_location is not None:
            if reg.get("poi_location"):
                raise HTTPException(422, "Hồ sơ đã có ghim vị trí của chủ quán")
            reg["poi_location"] = updates["poi_location"] = poi_location.model_dump()
        if action == "approve" and reg.get("poi_location"):
            if poi_id is not None or draft is not None:
                raise HTTPException(422, "Hồ sơ đã có ghim vị trí. Hãy duyệt từ thông tin trong hồ sơ.")
            linked_poi_id = await _publish_pinned_registration(reg, uid, user, ip, session=tx)
        elif action == "approve":
            if (poi_id is None) == (draft is None):
                raise HTTPException(422, "Chọn một quán có sẵn hoặc nhập thông tin tạo quán nháp")
            permission = "poi:create" if draft is not None else "poi:update"
            if permission not in user.get("permissions", []):
                raise HTTPException(403, f"Bạn không có quyền thực hiện thao tác này ({permission})")
            if draft is not None:
                name = (reg.get("poi_name") or "").strip()
                address = (reg.get("poi_address") or "").strip()
                if not name or len(name) > 180 or not address or len(address) > 400:
                    raise HTTPException(422, "Tên hoặc địa chỉ trong hồ sơ không hợp lệ")
                duplicate = await db["poi"].find_one(
                    _registration_poi_identity(reg), {"_id": 1}, session=tx,
                )
                if duplicate:
                    raise HTTPException(409, "Đã có quán trùng tên và địa chỉ. Hãy tìm lại và chọn quán có sẵn.")
                image = (reg.get("storefront_image_url") or "").strip()
                payload = POICreateRequest(
                    name=name, address=address, images=[image] if 0 < len(image) <= 2048 else [],
                    **draft.model_dump(),
                )
                linked_poi_id = await insert_poi(payload, user, ip, session=tx, owner_id=uid)
            else:
                linked_poi_id = _object_id(poi_id, "POI ID")
                linked = await db["poi"].update_one(
                    {"_id": linked_poi_id, "$or": [{"owner_id": None}, {"owner_id": {"$in": [uid, str(uid)]}}]},
                    {"$set": {"owner_id": uid, "updated_at": stamp}}, session=tx,
                )
                if not linked.matched_count:
                    if not await db["poi"].find_one({"_id": linked_poi_id}, {"_id": 1}, session=tx):
                        raise HTTPException(404, "Không tìm thấy quán để gắn")
                    raise HTTPException(409, "Quán đã được gắn cho một chủ sở hữu khác")
                await bump_dataset(session=tx)
        if linked_poi_id is not None:
            updates["linked_poi_id"] = linked_poi_id
            await db["users"].update_one({"_id": uid}, {"$set": {
                "is_poi_owner_verified": True, "updated_at": stamp}}, session=tx)

        claimed = await db["poi_owner_registrations"].update_one(
            {"_id": rid, "status": previous_status, "linked_poi_id": None},
            {"$set": updates}, session=tx,
        )
        if not claimed.modified_count:
            raise HTTPException(409, "Hồ sơ đã được xử lý")

        message = ("Quán đã được công khai và gắn với tài khoản của bạn" if linked_poi_id and reg.get("poi_location")
                   else "Quán đã được gắn với tài khoản của bạn" if repairing
                   else "Hồ sơ đã được duyệt và quán đã được gắn" if action == "approve"
                   else f"Hồ sơ bị từ chối: {note}")
        await db["owner_notifications"].insert_one({
            "user_id": uid, "type": "registration_review", "registration_id": rid,
            "title": "Kết quả duyệt hồ sơ", "message": message,
            "admin_note": note or None, "is_read": False, "created_at": stamp,
        }, session=tx)
        audit_action = "owner.registration_link" if repairing else f"owner.registration_{action}"
        await write_audit_event(user.get("id"), audit_action, f"registration:{reg_id}", ip,
            {"status": new_status, "poi_name": reg.get("poi_name"), "has_note": bool(note),
             "linked_poi_id": str(linked_poi_id) if linked_poi_id else None,
             "created_draft": draft is not None}, session=tx)

    result = {"id": reg_id, "status": new_status}
    if linked_poi_id:
        result["poi_id"] = str(linked_poi_id)
    return result
