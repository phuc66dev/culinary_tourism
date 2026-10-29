"""User/Role management with RBAC, safe projections and audit trail."""
import asyncio
from datetime import datetime, timezone
import re
from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from app.core.database import get_db, mongo_transaction
from app.core.rbac import ALL_PERMISSIONS
from app.core.security import hash_password
from app.core.auth_sessions import revoke_all_sessions
from app.modules.admin.audit import write_audit_event


def now():
    return datetime.now(timezone.utc)


def valid_id(value):
    if not ObjectId.is_valid(value):
        raise HTTPException(400, "ID không hợp lệ")
    return ObjectId(value)


def serialize_user(doc):
    return {"id": str(doc["_id"]), "email": doc.get("email"),
            "full_name": doc.get("full_name"), "role": doc.get("role"),
            "is_active": doc.get("is_active", True),
            "is_poi_owner_verified": doc.get("is_poi_owner_verified", False),
            "must_change_password": doc.get("must_change_password", False),
            "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None}


def serialize_role(doc):
    return {"id": str(doc["_id"]), "name": doc["name"],
            "priority": doc.get("priority", 5), "permissions": sorted(doc.get("permissions", [])),
            "is_system": doc.get("is_system", False)}


def validate_permissions(perms):
    if len(perms) != len(set(perms)) or not set(perms).issubset(ALL_PERMISSIONS):
        raise HTTPException(422, "Permission trùng hoặc không nằm trong danh mục 32 quyền")


async def list_users(q=None, role=None, limit=50, skip=0):
    query = {"deleted_at": {"$exists": False}}
    if q:
        regex = {"$regex": re.escape(q.strip()), "$options": "i"}
        query["$or"] = [{"email": regex}, {"full_name": regex}]
    if role:
        query["role"] = role
    col = get_db()["users"]
    return {"items": [serialize_user(u) async for u in col.find(query).sort("created_at", -1).skip(skip).limit(limit)],
            "total": await col.count_documents(query), "limit": limit, "skip": skip}


async def list_roles():
    col = get_db()["roles"]
    return {"items": [serialize_role(d) async for d in col.find().sort("priority", 1)],
            "permission_catalog": sorted(ALL_PERMISSIONS)}


async def _assert_assignable_role(db, name, actor=None, session=None):
    if name == "super_admin":
        raise HTTPException(403, "Không thể cấp vai trò super_admin qua API")
    role = await db["roles"].find_one({"name": name}, session=session)
    if not role:
        raise HTTPException(422, "Vai trò không tồn tại")
    if actor is not None and actor.get("role") != "super_admin":
        actor_role = await db["roles"].find_one({"name": actor["role"]}, session=session)
        if (not actor_role or role.get("priority", 99) < actor_role.get("priority", 99)
                or not set(role.get("permissions", [])).issubset(actor["permissions"])):
            raise HTTPException(403, "Không thể cấp vai trò có đặc quyền cao hơn tài khoản hiện tại")


async def _guard_target(db, doc, actor, session=None):
    if doc.get("role") == "super_admin":
        raise HTTPException(403, "Không thể quản trị tài khoản super_admin qua API")
    if actor["role"] == "super_admin":
        return
    target_role = await db["roles"].find_one({"name": doc.get("role")}, session=session)
    actor_role = await db["roles"].find_one({"name": actor["role"]}, session=session)
    if (not target_role or not actor_role or target_role.get("priority", 99) < actor_role.get("priority", 99)
            or not set(target_role.get("permissions", [])).issubset(actor["permissions"])):
        raise HTTPException(403, "Không thể thay đổi tài khoản có đặc quyền cao hơn")


async def create_user(payload, actor, ip):
    db = get_db()
    await _assert_assignable_role(db, payload.role, actor)
    doc = {"email": payload.email.strip().lower(), "full_name": payload.full_name,
           "password_hash": await asyncio.to_thread(hash_password, payload.password),
           "role": payload.role, "is_active": payload.is_active, "is_poi_owner_verified": False,
           "must_change_password": True, "token_version": 0, "created_at": now(), "updated_at": now()}
    try:
        async with mongo_transaction() as tx:
            res = await db["users"].insert_one(doc, session=tx)
            await write_audit_event(actor["id"], "user.create", f"user:{res.inserted_id}", ip,
                                    {"role": payload.role, "is_active": payload.is_active,
                                     "after": {"full_name": payload.full_name,
                                               "role": payload.role, "is_active": payload.is_active}}, session=tx)
    except DuplicateKeyError as exc:
        raise HTTPException(409, "Email đã tồn tại") from exc
    return serialize_user({**doc, "_id": res.inserted_id})


async def update_user(user_id, payload, actor, ip):
    uid = valid_id(user_id)
    if user_id == actor["id"]:
        raise HTTPException(403, "Không được tự thay đổi vai trò hoặc trạng thái tài khoản")
    fields = payload.model_dump(exclude_unset=True)
    if not fields or any(value is None for value in fields.values()):
        raise HTTPException(422, "Không có nội dung cập nhật hợp lệ")
    db = get_db()
    async with mongo_transaction() as tx:
        doc = await db["users"].find_one({"_id": uid, "deleted_at": {"$exists": False}}, session=tx)
        if not doc:
            raise HTTPException(404, "Không tìm thấy tài khoản")
        await _guard_target(db, doc, actor, tx)
        if "role" in fields:
            await _assert_assignable_role(db, fields["role"], actor, tx)
        change_security = "role" in fields or fields.get("is_active") is False
        update = {"$set": {**fields, "updated_at": now()}}
        if change_security:
            update["$inc"] = {"token_version": 1}
        await db["users"].update_one({"_id": uid}, update, session=tx)
        if change_security:
            await revoke_all_sessions(user_id, session=tx)
        tracked = ("full_name", "role", "is_active")
        before = {key: doc.get(key) for key in tracked if key in fields}
        after = {key: fields[key] for key in tracked if key in fields}
        await write_audit_event(actor["id"], "user.update", f"user:{user_id}", ip,
                                {"changed_fields": list(fields), "before": before, "after": after}, session=tx)
        doc.update(fields)
    return serialize_user(doc)


async def delete_user(user_id, actor, ip):
    uid = valid_id(user_id)
    if user_id == actor["id"]:
        raise HTTPException(403, "Không được tự xóa tài khoản")
    db = get_db()
    async with mongo_transaction() as tx:
        doc = await db["users"].find_one({"_id": uid, "deleted_at": {"$exists": False}}, session=tx)
        if not doc:
            raise HTTPException(404, "Không tìm thấy tài khoản")
        await _guard_target(db, doc, actor, tx)
        await db["users"].update_one({"_id": uid}, {"$set": {"is_active": False,
            "deleted_at": now(), "updated_at": now()}, "$inc": {"token_version": 1}}, session=tx)
        await revoke_all_sessions(user_id, session=tx)
        await write_audit_event(actor["id"], "user.soft_delete", f"user:{user_id}", ip,
                                {"role": doc.get("role"),
                                 "before": {"is_active": doc.get("is_active", True)},
                                 "after": {"is_active": False}}, session=tx)
    return {"id": user_id, "deleted": True}


async def reset_password(user_id, payload, actor, ip):
    uid = valid_id(user_id)
    if user_id == actor["id"]:
        raise HTTPException(403, "Dùng chức năng đổi mật khẩu cá nhân")
    db = get_db()
    hashed = await asyncio.to_thread(hash_password, payload.password)
    async with mongo_transaction() as tx:
        doc = await db["users"].find_one({"_id": uid, "deleted_at": {"$exists": False}}, session=tx)
        if not doc:
            raise HTTPException(404, "Không tìm thấy tài khoản")
        await _guard_target(db, doc, actor, tx)
        await db["users"].update_one({"_id": uid}, {"$set": {"password_hash": hashed,
            "must_change_password": True, "updated_at": now()}, "$inc": {"token_version": 1}}, session=tx)
        await revoke_all_sessions(user_id, session=tx)
        await write_audit_event(actor["id"], "user.password_reset", f"user:{user_id}", ip, session=tx)
    return {"message": "Đã đặt lại mật khẩu; tài khoản phải đổi sau khi đăng nhập"}


async def create_role(payload, actor, ip):
    validate_permissions(payload.permissions)
    db = get_db()
    if actor["role"] != "super_admin":
        existing = await db["roles"].find_one({"name": actor["role"]})
        if not existing or payload.priority < existing.get("priority", 99) or not set(payload.permissions).issubset(actor["permissions"]):
            raise HTTPException(403, "Không thể tạo vai trò có quyền hoặc độ ưu tiên cao hơn của bạn")
    doc = {**payload.model_dump(), "is_system": False, "created_at": now(), "updated_at": now()}
    try:
        async with mongo_transaction() as tx:
            res = await db["roles"].insert_one(doc, session=tx)
            await write_audit_event(actor["id"], "role.create", f"role:{payload.name}", ip,
                                    {"permissions": payload.permissions}, session=tx)
    except DuplicateKeyError as exc:
        raise HTTPException(409, "Tên vai trò đã tồn tại") from exc
    return serialize_role({**doc, "_id": res.inserted_id})


async def update_role(name, payload, actor, ip):
    validate_permissions(payload.permissions)
    if name == "super_admin":
        raise HTTPException(403, "Không thể chỉnh sửa quyền super_admin")
    db = get_db()
    patch = {"permissions": payload.permissions, "updated_at": now()}
    if payload.priority is not None:
        patch["priority"] = payload.priority
    async with mongo_transaction() as tx:
        doc = await db["roles"].find_one({"name": name}, session=tx)
        if not doc:
            raise HTTPException(404, "Không có vai trò")
        if actor["role"] != "super_admin":
            actor_role = await db["roles"].find_one({"name": actor["role"]}, session=tx)
            if not actor_role or doc.get("priority", 99) < actor_role.get("priority", 99) or not set(payload.permissions).issubset(actor["permissions"]):
                raise HTTPException(403, "Không thể cấp đặc quyền cao hơn của bạn")
            if payload.priority is not None and payload.priority < actor_role.get("priority", 99):
                raise HTTPException(403, "Không thể đặt độ ưu tiên cao hơn của bạn")
        await db["roles"].update_one({"name": name}, {"$set": patch}, session=tx)
        await write_audit_event(actor["id"], "role.update", f"role:{name}", ip,
                                {"permissions": payload.permissions}, session=tx)
    return serialize_role({**doc, **patch})


async def delete_role(name, actor, ip):
    if name == "super_admin":
        raise HTTPException(403, "Không thể xóa super_admin")
    db = get_db()
    async with mongo_transaction() as tx:
        doc = await db["roles"].find_one({"name": name}, session=tx)
        if not doc:
            raise HTTPException(404, "Không tìm thấy vai trò")
        if doc.get("is_system"):
            raise HTTPException(403, "Không thể xóa vai trò hệ thống")
        if await db["users"].count_documents({"role": name, "deleted_at": {"$exists": False}}, session=tx):
            raise HTTPException(409, "Vai trò đang được tài khoản sử dụng")
        await db["roles"].delete_one({"name": name}, session=tx)
        await write_audit_event(actor["id"], "role.delete", f"role:{name}", ip, session=tx)
    return {"name": name, "deleted": True}
