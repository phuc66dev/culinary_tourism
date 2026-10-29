from datetime import datetime, timezone
import re
import unicodedata

from bson import ObjectId
from fastapi import HTTPException

from app.core.database import get_db, mongo_transaction
from app.core.cache import cache_get_json, cache_set_json
import hashlib
import json
from app.modules.admin.schemas import POICreateRequest, POIUpdateRequest
from app.modules.audio.source_version import source_fingerprint


def now():
    return datetime.now(timezone.utc)


def oid(value, label="POI"):
    if not ObjectId.is_valid(str(value)):
        raise HTTPException(400, f"{label} ID không hợp lệ")
    return ObjectId(str(value))


def revision_query(doc):
    return {"revision": doc["revision"]} if "revision" in doc else {"revision": {"$exists": False}}


def slugify(value):
    text = unicodedata.normalize("NFKD", value).replace("đ", "d").replace("Đ", "D")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", text))[:70] or "quan-an"


# Vietnamese accent-insensitive name search, including đ/d and pre-existing data.
# Expand characters into explicit variants (not user-supplied regex) so old POIs
# are searchable immediately without a new field / migration.
_SEARCH_GROUPS = (
    "aàáảãạăằắẳẵặâầấẩẫậ",
    "eèéẻẽẹêềếểễệ",
    "iìíỉĩị",
    "oòóỏõọôồốổỗộơờớởỡợ",
    "uùúủũụưừứửữự",
    "yỳýỷỹỵ",
    "dđ",
)
_SEARCH_VARIANTS = {ch: "[" + group + "]" for group in _SEARCH_GROUPS for ch in group}
_COMBINING_MARKS = "[\u0300-\u036f]*"


def vietnamese_search_regex(value: str) -> str:
    """Substring pattern treating 'trang', 'tráng' and 'trắng' alike.

    Normalized to decomposed Unicode; escape non-letters so operators entered
    by users are literals. Combining mark ranges also allow decomposed Unicode spelling.
    """
    folded = unicodedata.normalize("NFD", value.strip().casefold())
    folded = "".join(c for c in folded if not unicodedata.combining(c)).replace("đ", "d")
    return "".join(
        (_SEARCH_VARIANTS.get(ch, re.escape(ch)) + _COMBINING_MARKS)
        if ch.isalpha() else re.escape(ch)
        for ch in folded
    )


def localized_ready(en):
    problems = []
    if not en or not str(en.get("title") or "").strip():
        problems.append("Thiếu tên quán bằng tiếng Anh")
    if not en or not str(en.get("description") or "").strip():
        problems.append("Thiếu mô tả tiếng Anh")
    if not en or en.get("audio_status") != "completed" or not str(en.get("audio_url") or "").strip():
        problems.append("Chưa hoàn tất âm thanh tiếng Anh")
    return {"ready": not problems, "reasons": problems}


async def gate_for(poi_id, session=None):
    en = await get_db()["poi_localizations"].find_one({"poi_id": poi_id, "lang": "en"}, session=session)
    gate = localized_ready(en)
    return {**gate, "en": {"title": (en or {}).get("title"),
                           "description": (en or {}).get("description"),
                           "audio_status": (en or {}).get("audio_status"),
                           "audio_url": (en or {}).get("audio_url")}}


def serialize_poi(doc, gate):
    location = doc.get("location") or {}
    return {
        "id": str(doc["_id"]), "slug": doc.get("slug"), "name": doc.get("name"),
        "address": doc.get("address"), "ward": doc.get("ward"), "category": doc.get("category"),
        "location": location, "original_description": doc.get("original_description"),
        "images": doc.get("images") or [], "trigger_radius": doc.get("trigger_radius", 30),
        "audio_priority": doc.get("audio_priority", 5), "is_active": bool(doc.get("is_active")),
        "revision": doc.get("revision", 0), "activation": gate,
        "created_at": doc["created_at"].isoformat() if isinstance(doc.get("created_at"), datetime) else None,
        "updated_at": doc["updated_at"].isoformat() if isinstance(doc.get("updated_at"), datetime) else None,
    }


async def bump_dataset(session=None):
    result = await get_db()["system_meta"].find_one_and_update(
        {"_id": "dataset"},
        {"$inc": {"version": 1}, "$set": {"updated_at": now()}}, upsert=True, return_document=True, session=session,
    )
    return result["version"]


async def invalidate_narrations(db, pid, name, description, *, name_changed, desc_changed, session):
    """Invalidate ALL languages after source changes, within the POI transaction.

    Existing translations lose provenance and audio URL; they cannot accidentally
    be reused even if another Audio worker races with a POI edit.
    Vietnamese localization is synced to the authoritative POI source immediately.
    """
    stamp = now()
    reset = {"audio_status": "pending", "audio_url": None, "updated_at": stamp}
    if name_changed:
        reset["title"] = None
    if desc_changed:
        reset["description"] = None
    await db["poi_localizations"].update_many(
        {"poi_id": pid, "lang": {"$in": ["en", "zh", "ja", "ko"]}},
        {"$set": reset, "$unset": {"source_hash": "", "translation_origin": ""}},
        session=session,
    )
    fingerprint = source_fingerprint(name, description)
    await db["poi_localizations"].update_one(
        {"poi_id": pid, "lang": "vi"},
        {"$set": {"title": name, "description": description, "source_hash": fingerprint,
                  "audio_url": None, "audio_status": "pending", "updated_at": stamp,
                  "translation_origin": "auto"},
         "$setOnInsert": {"created_at": stamp}},
        upsert=True, session=session,
    )


async def list_pois(q=None, ward=None, active=None, limit=200, skip=0):
    db = get_db()
    query = {}
    if q and q.strip():
        query["name"] = {"$regex": vietnamese_search_regex(q), "$options": "i"}
    if ward:
        query["ward"] = ward
    if active is not None:
        query["is_active"] = active
    dataset = await db["system_meta"].find_one({"_id": "dataset"}, {"version": 1}) or {}
    cache_args = {"version": dataset.get("version", 0), "query": query, "limit": limit, "skip": skip}
    cache_key = "admin:poi:list:" + hashlib.sha256(json.dumps(cache_args, sort_keys=True).encode()).hexdigest()
    cached = await cache_get_json(cache_key)
    if cached is not None:
        return cached
    total = await db["poi"].count_documents(query)
    docs = [d async for d in db["poi"].find(query).sort("name", 1).skip(skip).limit(limit)]
    ids = [d["_id"] for d in docs]
    en_docs = [d async for d in db["poi_localizations"].find({"poi_id": {"$in": ids}, "lang": "en"})] if ids else []
    en_by_id = {d["poi_id"]: d for d in en_docs}
    items = [serialize_poi(d, {**localized_ready(en_by_id.get(d["_id"])), "en": {
        "title": (en_by_id.get(d["_id"]) or {}).get("title"),
        "description": (en_by_id.get(d["_id"]) or {}).get("description"),
        "audio_url": (en_by_id.get(d["_id"]) or {}).get("audio_url"),
        "audio_status": (en_by_id.get(d["_id"]) or {}).get("audio_status"),
    }}) for d in docs]
    wards = sorted(v for v in await db["poi"].distinct("ward") if v)
    output = {"items": items, "total": total, "limit": limit, "skip": skip, "wards": wards}
    await cache_set_json(cache_key, output, ttl=10)
    return output


async def get_poi(poi_id):
    pid = oid(poi_id)
    doc = await get_db()["poi"].find_one({"_id": pid})
    if not doc:
        raise HTTPException(404, "Không tìm thấy quán")
    return serialize_poi(doc, await gate_for(pid))


async def create_poi(payload: POICreateRequest, user, ip):
    db = get_db()
    if payload.is_active:
        raise HTTPException(409, {"message": "Không thể công khai POI mới khi chưa có tiếng Anh và audio", "reasons": localized_ready(None)["reasons"]})
    stamp = now()
    doc = payload.model_dump(mode="python")
    doc["location"] = payload.location.model_dump(mode="python")
    doc.update({"is_active": False, "slug": f"{slugify(payload.name)}-{str(ObjectId())[:8]}",
                "revision": 1, "created_at": stamp, "updated_at": stamp})
    from app.modules.admin.audit import write_audit_event
    async with mongo_transaction() as tx:
        result = await db["poi"].insert_one(doc, session=tx)
        version = await bump_dataset(session=tx)
        await write_audit_event(user["id"], "poi.create", f"poi:{result.inserted_id}", ip,
                                {"dataset_version": version}, session=tx)
    return await get_poi(str(result.inserted_id))


async def update_poi(poi_id, payload: POIUpdateRequest, user, ip):
    db = get_db()
    pid = oid(poi_id)
    existing = await db["poi"].find_one({"_id": pid})
    if not existing:
        raise HTTPException(404, "Không tìm thấy quán")
    data = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
    if not data:
        raise HTTPException(422, "Không có trường nào để cập nhật")
    if any(v is None for v in data.values()):
        raise HTTPException(422, "Không thể đặt trường POI thành null")
    if payload.expected_revision is not None and payload.expected_revision != existing.get("revision", 0):
        raise HTTPException(409, "POI đã được cập nhật bởi quản trị viên khác; hãy tải lại")
    if "location" in data:
        data["location"] = payload.location.model_dump()
    if data.get("is_active") is True:
        gate = await gate_for(pid)
        if not gate["ready"]:
            raise HTTPException(409, {"message": "Activation Gate chưa đạt", "reasons": gate["reasons"]})
    # Nội dung gốc đổi -> audio EN cũ cần được tạo lại trước khi được công khai.
    desc_changed = "original_description" in data and data["original_description"] != existing.get("original_description")
    name_changed = "name" in data and data["name"] != existing.get("name")
    narrative_changed = desc_changed or name_changed
    if narrative_changed and data.get("is_active", existing.get("is_active", False)):
        raise HTTPException(409, "Hãy tắt công khai quán trước khi đổi mô tả để tạo lại audio tiếng Anh")
    from app.modules.admin.audit import write_audit_event
    async with mongo_transaction() as tx:
        if data.get("is_active") is True:
            gate = await gate_for(pid, session=tx)
            if not gate["ready"]:
                raise HTTPException(409, {"message": "Activation Gate chưa đạt", "reasons": gate["reasons"]})
        updated = await db["poi"].update_one(
            {"_id": pid, **revision_query(existing)},
            {"$set": {**data, "updated_at": now()}, "$inc": {"revision": 1}}, session=tx)
        if not updated.modified_count:
            raise HTTPException(409, "POI vừa thay đổi; hãy tải lại")
        if narrative_changed:
            await invalidate_narrations(
                db, pid, data.get("name", existing.get("name", "")),
                data.get("original_description", existing.get("original_description", "")),
                name_changed=name_changed, desc_changed=desc_changed, session=tx,
            )
        version = await bump_dataset(session=tx)
        await write_audit_event(user["id"], "poi.update", f"poi:{pid}", ip,
                                {"fields": list(data), "dataset_version": version}, session=tx)
    return await get_poi(poi_id)


async def delete_poi(poi_id, user, ip):
    db = get_db()
    pid = oid(poi_id)
    if await db["poi_submissions"].count_documents({"poi_id": {"$in": [pid, str(pid)]}, "status": "pending"}):
        raise HTTPException(409, "Còn đề xuất chỉnh sửa đang chờ duyệt; xử lý trước khi xóa")
    snapshot = await db["poi"].find_one({"_id": pid}, {"name": 1, "address": 1, "ward": 1})
    if snapshot is None:
        raise HTTPException(404, "Không tìm thấy quán")
    # Persist a security audit before destructive writes without importing admin_service.
    # This keeps the POI module independent of admin/service.py at startup.
    from app.modules.admin.audit import write_audit_event
    import logging
    try:
        await write_audit_event(user["id"], "poi.delete_requested", f"poi:{pid}", ip,
                                {"poi_name": snapshot.get("name"), "ward": snapshot.get("ward")})
    except Exception:
        logging.getLogger("quan4.admin").exception("Unable to audit POI deletion request")
        raise HTTPException(503, "Cannot persist security audit event") from None
    async with mongo_transaction() as tx:
        deleted = await db["poi"].delete_one({"_id": pid}, session=tx)
        if not deleted.deleted_count:
            raise HTTPException(409, "POI đã được xóa bởi yêu cầu khác")
        localizations_deleted = await db["poi_localizations"].delete_many({"poi_id": pid}, session=tx)
        menu_deleted = await db["menu_items"].delete_many({"poi_id": {"$in": [pid, str(pid)]}}, session=tx)
        version = await bump_dataset(session=tx)
        await write_audit_event(user["id"], "poi.delete", f"poi:{pid}", ip,
            {"poi_name": snapshot.get("name"), "address": snapshot.get("address"),
             "ward": snapshot.get("ward"), "deleted_poi": deleted.deleted_count,
             "deleted_localizations": localizations_deleted.deleted_count,
             "deleted_menu_items": menu_deleted.deleted_count, "dataset_version": version}, session=tx)
    return {"id": str(pid), "deleted": True, "dataset_version": version}


async def save_english(poi_id, payload, user, ip):
    """Lưu nội dung tiếng Anh thủ công; phải tạo lại audio khi nội dung TTS đổi."""
    db = get_db()
    pid = oid(poi_id)
    poi = await db["poi"].find_one({"_id": pid})
    if not poi:
        raise HTTPException(404, "Không tìm thấy quán")
    if payload.expected_revision != poi.get("revision", 0):
        raise HTTPException(409, "Phiên bản POI đã đổi; hãy tải lại")
    en = await db["poi_localizations"].find_one({"poi_id": pid, "lang": "en"}) or {}
    content_changed = payload.title != en.get("title") or payload.description != en.get("description")
    if content_changed and poi.get("is_active"):
        raise HTTPException(409, "Hãy tắt công khai quán trước khi thay đổi bản dịch tiếng Anh")
    if not content_changed:
        return await get_poi(poi_id)
    from app.modules.admin.audit import write_audit_event
    async with mongo_transaction() as tx:
        res = await db["poi"].update_one({"_id": pid, **revision_query(poi)},
            {"$inc": {"revision": 1}, "$set": {"updated_at": now()}}, session=tx)
        if not res.modified_count:
            raise HTTPException(409, "POI vừa thay đổi; hãy tải lại")
        await db["poi_localizations"].update_one({"poi_id": pid, "lang": "en"},
            {"$set": {"title": payload.title, "description": payload.description,
                      "source_hash": source_fingerprint(
                          poi.get("name", ""), poi.get("original_description") or poi.get("description") or ""),
                      "translation_origin": "manual",
                      "audio_status": "pending", "audio_url": None, "updated_at": now()},
             "$setOnInsert": {"created_at": now(), "is_fallback": False}}, upsert=True, session=tx)
        version = await bump_dataset(session=tx)
        await write_audit_event(user["id"], "poi.english_update", f"poi:{pid}", ip,
                                {"dataset_version": version}, session=tx)
    return await get_poi(poi_id)
