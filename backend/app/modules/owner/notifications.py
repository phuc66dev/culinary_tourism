"""Owner inbox: results of registration/submission reviews.

Only the owner can view their own messages; CCCD must never appear in notifications.
"""
from bson import ObjectId
from fastapi import HTTPException
from app.core.database import get_db


def owner_query(user):
    uid = user["id"]
    if not ObjectId.is_valid(uid):
        raise HTTPException(401, "Invalid owner session")
    return {"user_id": {"$in": [ObjectId(uid), uid]}}


def serialize(doc):
    return {"id": str(doc["_id"]), "type": doc.get("type"), "title": doc.get("title"),
            "message": doc.get("message"), "admin_note": doc.get("admin_note"),
            "is_read": bool(doc.get("is_read", False)),
            "created_at": doc["created_at"].isoformat() if doc.get("created_at") else None}


async def list_notifications(user, limit=50, skip=0):
    db = get_db()
    query = owner_query(user)
    total = await db["owner_notifications"].count_documents(query)
    unread = await db["owner_notifications"].count_documents({**query, "is_read": False})
    docs = [d async for d in db["owner_notifications"].find(query)
            .sort("created_at", -1).skip(skip).limit(limit)]
    return {"items": [serialize(d) for d in docs], "total": total, "unread_count": unread}


async def read_notification(notification_id, user):
    if not ObjectId.is_valid(notification_id):
        raise HTTPException(400, "Notification ID không hợp lệ")
    db = get_db()
    query = {"_id": ObjectId(notification_id), **owner_query(user)}
    doc = await db["owner_notifications"].find_one(query)
    if not doc:
        raise HTTPException(404, "Không tìm thấy thông báo")
    if not doc.get("is_read"):
        await db["owner_notifications"].update_one(query, {"$set": {"is_read": True}})
        doc["is_read"] = True
    return serialize(doc)
