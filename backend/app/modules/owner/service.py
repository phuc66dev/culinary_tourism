"""Owner Portal business rules and owner-scoped MongoDB operations."""
import asyncio
import re
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.database import get_db, mongo_transaction
from app.core.security import encrypt_pii, hash_password
from app.modules.admin.audit import write_audit_event
from app.modules.admin.schemas import POIUpdateRequest
from app.modules.owner.schemas import (
    MenuItemRequest,
    MenuItemUpdateRequest,
    OwnerPOIAvailabilityRequest,
    OwnerRegisterRequest,
    POISubmissionRequest,
)


def now() -> datetime:
    return datetime.now(timezone.utc)


def owner_object_id(user: dict) -> ObjectId:
    try:
        return ObjectId(user["id"])
    except (InvalidId, KeyError, TypeError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Phiên chủ quán không hợp lệ") from exc


def owner_id_values(user: dict) -> list:
    oid = owner_object_id(user)
    return [oid, str(oid)]


def ensure_verified_owner(user: dict) -> ObjectId:
    oid = owner_object_id(user)
    if not user.get("is_poi_owner_verified", False):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Hồ sơ chủ quán chưa được xác minh")
    return oid


async def _owned_poi(poi_id: str, user: dict) -> dict:
    owner_id = ensure_verified_owner(user)
    if not ObjectId.is_valid(poi_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "POI ID không hợp lệ")
    poi = await get_db()["poi"].find_one({
        "_id": ObjectId(poi_id), "owner_id": {"$in": [owner_id, str(owner_id)]},
    })
    if not poi:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy quán thuộc tài khoản của bạn")
    return poi


def _serialize_poi(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "category": doc.get("category"),
        "address": doc.get("address"),
        "ward": doc.get("ward"),
        "location": doc.get("location"),
        "original_description": doc.get("original_description"),
        "images": doc.get("images") or [],
        "opening_hours": doc.get("opening_hours"),
        "is_open": doc.get("is_open"),
        "is_active": bool(doc.get("is_active", False)),
        "revision": int(doc.get("revision", 0)),
    }


def _menu_images(doc: dict) -> list[str]:
    images = doc.get("image_urls")
    if images is not None:
        return images
    return [doc["image_url"]] if doc.get("image_url") else []


def _serialize_menu_item(doc: dict) -> dict:
    images = _menu_images(doc)
    return {
        "id": str(doc["_id"]),
        "poi_id": str(doc.get("poi_id", "")),
        "name": doc.get("name"),
        "price_vnd": doc.get("price_vnd"),
        "image_url": images[0] if images else None,
        "image_urls": images,
        "tags": doc.get("tags") or [],
        "created_at": doc["created_at"].isoformat() if doc.get("created_at") else None,
        "updated_at": doc["updated_at"].isoformat() if doc.get("updated_at") else None,
    }


async def create_owner_registration(
    payload: OwnerRegisterRequest, client_ip: str | None, *, storefront_image: bytes | None = None,
) -> dict:
    """Create an owner account and pending verification application atomically."""
    db = get_db()
    email = str(payload.email).strip().lower()
    if await db["users"].find_one({"email": email}, {"_id": 1}):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email đã được sử dụng")

    # Fail before creating an account if PII encryption is unavailable.
    encrypted_cccd = encrypt_pii(payload.cccd_number)
    password_hash = await asyncio.to_thread(hash_password, payload.password)
    storefront_image_url = payload.storefront_image_url
    if storefront_image is not None:
        storefront_image_url = await asyncio.to_thread(_store_image, storefront_image, "storefront")
    stamp = now()
    registration_id = None
    try:
        async with mongo_transaction() as tx:
            user_result = await db["users"].insert_one({
                "email": email,
                "password_hash": password_hash,
                "full_name": payload.full_name,
                "phone": payload.phone,
                "role": "poi_owner",
                "is_active": True,
                "is_poi_owner_verified": False,
                "must_change_password": False,
                "created_at": stamp,
                "updated_at": stamp,
            }, session=tx)
            registration = {
                "user_id": user_result.inserted_id,
                "full_name": payload.full_name,
                "phone": payload.phone,
                "poi_name": payload.poi_name,
                "poi_address": payload.poi_address,
                "storefront_image_url": storefront_image_url,
                "cccd_encrypted": encrypted_cccd,
                "cccd_expires_at": stamp + timedelta(days=settings.PII_RETENTION_DAYS),
                "status": "pending",
                "created_at": stamp,
            }
            registration_result = await db["poi_owner_registrations"].insert_one(registration, session=tx)
            registration_id = registration_result.inserted_id
            await write_audit_event(
                None,
                "owner.registration_created",
                f"registration:{registration_id}",
                client_ip,
                {"poi_name": payload.poi_name},
                session=tx,
            )
    except DuplicateKeyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email đã được sử dụng") from exc

    return {
        "id": str(registration_id),
        "email": email,
        "status": "pending_verification",
        "is_poi_owner_verified": False,
    }


async def get_registration_status(user: dict) -> dict:
    uid = owner_object_id(user)
    db = get_db()
    registration = await db["poi_owner_registrations"].find_one(
        {"user_id": {"$in": [uid, str(uid)]}}, sort=[("created_at", -1)]
    )
    verified = bool(user.get("is_poi_owner_verified", False))
    return {
        "status": registration.get("status") if registration else ("approved" if verified else "not_submitted"),
        "is_poi_owner_verified": verified,
        "poi_name": registration.get("poi_name") if registration else None,
        "admin_note": registration.get("admin_note") if registration else None,
        "created_at": registration["created_at"].isoformat() if registration and registration.get("created_at") else None,
        "reviewed_at": registration["reviewed_at"].isoformat() if registration and registration.get("reviewed_at") else None,
    }


async def list_my_pois(user: dict) -> dict:
    owner_id = ensure_verified_owner(user)
    cursor = get_db()["poi"].find({"owner_id": {"$in": [owner_id, str(owner_id)]}}).sort("name", 1)
    items = [_serialize_poi(doc) async for doc in cursor]
    return {"items": items, "total": len(items)}


async def update_poi_availability(poi_id: str, payload: OwnerPOIAvailabilityRequest, user: dict, client_ip: str | None) -> dict:
    poi = await _owned_poi(poi_id, user)
    stamp = now()
    owner_filter = {"_id": poi["_id"], "owner_id": {"$in": owner_id_values(user)}}
    if "revision" in poi:
        owner_filter["revision"] = poi["revision"]
    else:
        owner_filter["revision"] = {"$exists": False}
    result = await get_db()["poi"].update_one(
        owner_filter,
        {"$set": {"is_open": payload.is_open, "updated_at": stamp}, "$inc": {"revision": 1}},
    )
    if not result.modified_count:
        raise HTTPException(status.HTTP_409_CONFLICT, "Quán vừa được cập nhật; hãy tải lại dữ liệu")
    await write_audit_event(user["id"], "owner.poi_availability_updated", f"poi:{poi_id}", client_ip,
                            {"is_open": payload.is_open})
    return {"id": poi_id, "is_open": payload.is_open, "revision": poi.get("revision", 0) + 1}


async def list_my_menu_items(poi_id: str, user: dict) -> dict:
    poi = await _owned_poi(poi_id, user)
    query = {"poi_id": {"$in": [poi["_id"], str(poi["_id"])]}}
    cursor = get_db()["menu_items"].find(query).sort("name", 1)
    items = [_serialize_menu_item(doc) async for doc in cursor]
    return {"items": items, "total": len(items)}


MENU_IMAGE_MAX_BYTES = 5 * 1024 * 1024
IMAGE_DIR = Path(__file__).resolve().parents[2] / "static" / "images"


async def authorize_menu_image_upload(poi_id: str, user: dict, menu_item_id: str | None):
    if menu_item_id:
        item = await _owned_menu_item(menu_item_id, user)
        if str(item["poi_id"]) != poi_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy món tại quán này")
    else:
        await _owned_poi(poi_id, user)


def store_menu_image(content: bytes) -> str:
    return _store_image(content, "menu")


def _store_image(content: bytes, folder: str) -> str:
    if len(content) > MENU_IMAGE_MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Ảnh vượt quá 5 MB")
    if content.startswith(b"\xff\xd8\xff"):
        extension = "jpg"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        extension = "png"
    elif content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        extension = "webp"
    else:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Chỉ hỗ trợ ảnh JPEG, PNG và WebP")
    filename = f"{sha256(content).hexdigest()}.{extension}"
    directory = IMAGE_DIR / folder
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename
    if not target.exists():
        temp_path = None
        try:
            with NamedTemporaryFile(dir=directory, suffix=".tmp", delete=False) as temp:
                temp_path = Path(temp.name)
                temp.write(content)
            temp_path.replace(target)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
    return f"/static/images/{folder}/{filename}"


async def create_menu_item(payload: MenuItemRequest, user: dict, client_ip: str | None) -> dict:
    poi = await _owned_poi(payload.poi_id, user)
    stamp = now()
    doc = {**payload.model_dump(exclude={"poi_id"}), "poi_id": poi["_id"], "owner_id": owner_object_id(user),
           "created_at": stamp, "updated_at": stamp}
    doc["image_urls"] = _menu_images(doc)
    doc["image_url"] = doc["image_urls"][0] if doc["image_urls"] else None
    result = await get_db()["menu_items"].insert_one(doc)
    doc["_id"] = result.inserted_id
    await write_audit_event(user["id"], "owner.menu_item_created", f"menu_item:{result.inserted_id}", client_ip,
                            {"poi_id": str(poi["_id"])})
    return _serialize_menu_item(doc)


async def _owned_menu_item(menu_item_id: str, user: dict) -> dict:
    owner_id = ensure_verified_owner(user)
    if not ObjectId.is_valid(menu_item_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Menu item ID không hợp lệ")
    doc = await get_db()["menu_items"].find_one({"_id": ObjectId(menu_item_id), "owner_id": {"$in": [owner_id, str(owner_id)]}})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy món thuộc quán của bạn")
    # Also verify the referenced POI still belongs to the same owner.
    await _owned_poi(str(doc.get("poi_id", "")), user)
    return doc


async def update_menu_item(menu_item_id: str, payload: MenuItemUpdateRequest, user: dict, client_ip: str | None) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    item = await _owned_menu_item(menu_item_id, user)
    if changes.get("image_urls") is not None:
        images = changes["image_urls"]
    elif "image_url" in changes:
        cover = changes["image_url"]
        images = [cover, *[url for url in _menu_images(item)[1:] if url != cover]] if cover else []
    else:
        images = None
        changes.pop("image_urls", None)
    if images is not None:
        changes["image_urls"] = images
        changes["image_url"] = images[0] if images else None
    if not changes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Chưa có nội dung cập nhật")
    changes["updated_at"] = now()
    await get_db()["menu_items"].update_one({"_id": item["_id"], "owner_id": {"$in": owner_id_values(user)}}, {"$set": changes})
    item.update(changes)
    await write_audit_event(user["id"], "owner.menu_item_updated", f"menu_item:{menu_item_id}", client_ip,
                            {"fields": [key for key in changes if key != "updated_at"]})
    return _serialize_menu_item(item)


async def delete_menu_item(menu_item_id: str, user: dict, client_ip: str | None) -> dict:
    item = await _owned_menu_item(menu_item_id, user)
    await get_db()["menu_items"].delete_one({"_id": item["_id"], "owner_id": {"$in": owner_id_values(user)}})
    await write_audit_event(user["id"], "owner.menu_item_deleted", f"menu_item:{menu_item_id}", client_ip,
                            {"poi_id": str(item.get("poi_id", ""))})
    return {"id": menu_item_id, "deleted": True}


async def create_poi_submission(payload: POISubmissionRequest, user: dict, client_ip: str | None) -> dict:
    poi = await _owned_poi(payload.poi_id, user)
    # Keep the owner lane aligned with the exact fields accepted by admin review.
    allowed = set(POIUpdateRequest.model_fields) - {"is_active", "expected_revision"}
    denied = set(payload.proposed_changes) - allowed
    if denied:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Không cho phép thay đổi: {', '.join(sorted(denied))}")
    try:
        parsed = POIUpdateRequest.model_validate(payload.proposed_changes)
    except Exception as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Nội dung đề xuất không hợp lệ") from exc
    changes = parsed.model_dump(exclude_unset=True)
    if not changes or any(value is None for value in changes.values()):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Đề xuất phải có giá trị hợp lệ")
    if all(poi.get(key) == value for key, value in changes.items()):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Đề xuất không có thay đổi thực tế")
    stamp = now()
    doc = {
        "poi_id": poi["_id"], "owner_id": owner_object_id(user),
        "proposed_changes": changes, "status": "pending",
        "poi_revision": poi.get("revision", 0), "created_at": stamp,
    }
    result = await get_db()["poi_submissions"].insert_one(doc)
    await write_audit_event(user["id"], "owner.poi_submission_created", f"submission:{result.inserted_id}", client_ip,
                            {"poi_id": str(poi["_id"]), "fields": list(changes)})
    return {"id": str(result.inserted_id), "poi_id": str(poi["_id"]), "status": "pending", "created_at": stamp.isoformat()}


async def list_my_submissions(
    user: dict, limit: int = 50, skip: int = 0, *,
    review_status: str | None = None, q: str = "",
    sort_by: str = "created_at", order: str = "desc",
) -> dict:
    owner_id = ensure_verified_owner(user)
    db = get_db()
    owner_filter = {"owner_id": {"$in": [owner_id, str(owner_id)]}}
    search_filter = dict(owner_filter)
    if q.strip():
        name_match = {"$regex": re.escape(q.strip()), "$options": "i"}
        poi_ids = [poi["_id"] async for poi in db["poi"].find({**owner_filter, "name": name_match}, {"_id": 1})]
        search_filter["$or"] = [
            {"poi_id": {"$in": poi_ids + [str(poi_id) for poi_id in poi_ids]}},
            {"proposed_changes.name": name_match},
        ]
    query = {**search_filter, "status": review_status} if review_status else search_filter
    collection = db["poi_submissions"]
    total = await collection.count_documents(query)
    direction = 1 if order == "asc" else -1
    docs = [doc async for doc in collection.find(query)
            .sort([(sort_by, direction), ("_id", direction)]).skip(skip).limit(limit)]
    items = []
    for doc in docs:
        poi_id = doc.get("poi_id")
        poi = await db["poi"].find_one({"_id": poi_id}) if isinstance(poi_id, ObjectId) else None
        items.append({
            "id": str(doc["_id"]), "poi_id": str(poi_id or ""),
            "poi_name": (poi or {}).get("name"), "status": doc.get("status"),
            "proposed_changes": doc.get("proposed_changes") or {},
            "admin_note": doc.get("admin_note"),
            "created_at": doc["created_at"].isoformat() if doc.get("created_at") else None,
            "reviewed_at": doc["reviewed_at"].isoformat() if doc.get("reviewed_at") else None,
        })
    counts = {state: await collection.count_documents({**search_filter, "status": state})
              for state in ("pending", "approved", "rejected")}
    return {"items": items, "counts": counts, "total": total, "limit": limit, "skip": skip}


async def get_dashboard_summary(user: dict) -> dict:
    owner_id = ensure_verified_owner(user)
    db = get_db()
    pois = [doc async for doc in db["poi"].find({"owner_id": {"$in": [owner_id, str(owner_id)]}}).sort("name", 1)]
    poi_ids = [doc["_id"] for doc in pois]
    poi_id_values = poi_ids + [str(pid) for pid in poi_ids]
    owned_filter = {"owner_id": {"$in": [owner_id, str(owner_id)]}}
    return {
        "pois": [_serialize_poi(doc) for doc in pois],
        "summary": {
            "poi_count": len(pois),
            "menu_item_count": await db["menu_items"].count_documents({"poi_id": {"$in": poi_id_values}}) if poi_ids else 0,
            "pending_submission_count": await db["poi_submissions"].count_documents({**owned_filter, "status": "pending"}),
            "unread_notification_count": await db["owner_notifications"].count_documents(
                {"user_id": {"$in": [owner_id, str(owner_id)]}, "is_read": False}
            ),
        },
    }


async def purge_expired_registration_pii() -> int:
    """Redact encrypted identity numbers after the configured retention window."""
    stamp = now()
    cutoff = stamp - timedelta(days=settings.PII_RETENTION_DAYS)
    query = {
        "$and": [
            {"$or": [
                {"cccd_expires_at": {"$lte": stamp}},
                {"cccd_expires_at": {"$exists": False}, "created_at": {"$lte": cutoff}},
            ]},
            {"$or": [
                {"cccd_encrypted": {"$exists": True}},
                {"encrypted_cccd": {"$exists": True}},
            ]},
        ]
    }
    result = await get_db()["poi_owner_registrations"].update_many(
        query,
        {"$unset": {"cccd_encrypted": "", "encrypted_cccd": ""},
         "$set": {"pii_redacted_at": stamp}},
    )
    return result.modified_count
