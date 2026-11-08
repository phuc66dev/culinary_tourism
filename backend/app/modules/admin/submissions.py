"""Task 3.6: inspect owner change requests, produce field-level diffs, review/merge.

Only POIUpdateRequest's explicit fields may be merged; user-supplied Mongo operators,
owner_id, slug, is_active, and internal revision are NEVER accepted in submissions.
"""
from datetime import datetime
import re

from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.database import get_db, mongo_transaction
from app.modules.admin.poi_management import (
    bump_dataset, gate_for, now, oid, revision_query, serialize_poi, invalidate_narrations,
)
from app.modules.admin.schemas import POIUpdateRequest

ALLOWED = frozenset(POIUpdateRequest.model_fields) - {"is_active", "expected_revision"}


def changes_for(doc):
    changes = doc.get("proposed_changes", {})
    if not isinstance(changes, dict) or not changes:
        raise HTTPException(422, "Đề xuất không có nội dung thay đổi")
    denied = set(changes) - ALLOWED
    if denied:
        raise HTTPException(422, f"Không cho phép thay đổi: {', '.join(sorted(denied))}")
    try:
        parsed = POIUpdateRequest.model_validate(changes)
    except ValidationError as error:
        raise HTTPException(422, error.errors(include_context=False, include_url=False)) from error
    clean = parsed.model_dump(exclude_unset=True)
    if any(value is None for value in clean.values()):
        raise HTTPException(422, "Giá trị null không hợp lệ")
    return clean


def serialize_submission(doc, poi):
    requested = doc.get("proposed_changes") or {}
    existing = {k: poi.get(k) if poi else None for k in requested} if isinstance(requested, dict) else {}
    diff = [
        {"field": field, "current": existing.get(field), "proposed": proposed,
         "changed": existing.get(field) != proposed}
        for field, proposed in (requested.items() if isinstance(requested, dict) else [])
    ]
    return {
        "id": str(doc["_id"]), "poi_id": str(doc.get("poi_id", "")),
        "owner_id": str(doc.get("owner_id") or doc.get("user_id") or ""),
        "poi_name": (poi or {}).get("name", "(POI không còn tồn tại)"),
        "status": doc.get("status"), "admin_note": doc.get("admin_note"),
        "proposed_changes": requested, "current_values": existing, "diff": diff,
        "poi_revision": poi.get("revision", 0) if poi else None,
        "created_at": doc["created_at"].isoformat() if isinstance(doc.get("created_at"), datetime) else None,
        "reviewed_at": doc["reviewed_at"].isoformat() if isinstance(doc.get("reviewed_at"), datetime) else None,
    }


async def list_submissions(status=None, q=None, limit=100, skip=0):
    """Filter at MongoDB BEFORE pagination, avoiding loading all submissions into RAM.

    POI IDs historically appear as either ObjectId or string in submissions.
    Search supports POI name and complete 24-character POI id.
    """
    db = get_db()
    if status and status not in ("pending", "approved", "rejected"):
        raise HTTPException(422, "Trạng thái không hợp lệ")
    query = {"status": status} if status else {}
    if q and q.strip():
        needle = q.strip()
        matching_pois = [p["_id"] async for p in db["poi"].find(
            {"name": {"$regex": re.escape(needle), "$options": "i"}}, {"_id": 1}
        )]
        if ObjectId.is_valid(needle):
            matching_pois.append(ObjectId(needle))
        poi_ids = list(set(matching_pois))
        query["poi_id"] = {"$in": poi_ids + [str(pid) for pid in poi_ids]}
    total = await db["poi_submissions"].count_documents(query)
    docs = [d async for d in db["poi_submissions"].find(query)
            .sort("created_at", -1).skip(skip).limit(limit)]
    ids = [ObjectId(str(d["poi_id"])) for d in docs
           if ObjectId.is_valid(str(d.get("poi_id", "")))]
    pois = [p async for p in db["poi"].find({"_id": {"$in": ids}})] if ids else []
    by_id = {p["_id"]: p for p in pois}
    items = [serialize_submission(d,
        by_id.get(ObjectId(str(d["poi_id"]))) if ObjectId.is_valid(str(d.get("poi_id", ""))) else None
    ) for d in docs]
    counts = {s: await db["poi_submissions"].count_documents({"status": s})
              for s in ("pending", "approved", "rejected")}
    return {"items": items, "total": total, "counts": counts, "limit": limit, "skip": skip}


async def review_submission(sub_id, action, note, expected_revision, user, ip):
    if action not in ("approve", "reject"):
        raise HTTPException(422, "action phải là approve hoặc reject")
    note = (note or "").strip()
    if action == "reject" and not note:
        raise HTTPException(422, "Phải nhập lý do từ chối")
    if len(note) > 500:
        raise HTTPException(422, "Ghi chú tối đa 500 ký tự")
    from app.modules.admin.audit import write_audit_event
    db = get_db()
    sid = oid(sub_id, "submission")
    version = None
    data = {}
    final_status = "approved" if action == "approve" else "rejected"
    async with mongo_transaction() as tx:
        submission = await db["poi_submissions"].find_one({"_id": sid}, session=tx)
        if not submission:
            raise HTTPException(404, "Không tìm thấy đề xuất")
        if submission.get("status") != "pending":
            raise HTTPException(409, "Đề xuất đã được xử lý")
        if action == "approve":
            data = changes_for(submission)
            pid = oid(submission.get("poi_id"))
            poi = await db["poi"].find_one({"_id": pid}, session=tx)
            if not poi:
                raise HTTPException(409, "Quán gốc không còn tồn tại")
            current_revision = poi.get("revision", 0)
            if not any(poi.get(key) != value for key, value in data.items()):
                raise HTTPException(422, "Đề xuất không có thay đổi thực tế")
            if expected_revision is None or expected_revision != current_revision:
                raise HTTPException(409, "POI đã đổi hoặc chưa xác nhận phiên bản; hãy tải lại Diff View")
            desc_changed = "original_description" in data and data["original_description"] != poi.get("original_description")
            name_changed = "name" in data and data["name"] != poi.get("name")
            if (desc_changed or name_changed) and poi.get("is_active"):
                raise HTTPException(409, "Phải tắt công khai quán trước khi duyệt thay đổi mô tả")
            updated = await db["poi"].update_one({"_id": pid, **revision_query(poi)},
                {"$set": {**data, "updated_at": now()}, "$inc": {"revision": 1}}, session=tx)
            if not updated.modified_count:
                raise HTTPException(409, "POI vừa thay đổi; tải lại Diff View")
            if desc_changed or name_changed:
                await invalidate_narrations(
                    db, pid, data.get("name", poi.get("name", "")),
                    data.get("original_description", poi.get("original_description", "")),
                    name_changed=name_changed, desc_changed=desc_changed, session=tx,
                )
            version = await bump_dataset(session=tx)
        claim = await db["poi_submissions"].update_one({"_id": sid, "status": "pending"},
            {"$set": {"status": final_status, "admin_note": note or None,
                      "reviewed_by": user["id"], "reviewed_at": now(), "dataset_version": version}}, session=tx)
        if not claim.modified_count:
            raise HTTPException(409, "Đề xuất đã được duyệt ở yêu cầu khác")
        owner_id = submission.get("owner_id") or submission.get("user_id")
        if owner_id:
            uid = oid(owner_id, "owner")
            await db["owner_notifications"].insert_one({
                "user_id": uid, "type": "submission_review", "submission_id": sid,
                "title": "Kết quả duyệt thay đổi thông tin quán",
                "message": "Thay đổi đã được phê duyệt" if action == "approve" else f"Đề xuất bị từ chối: {note}",
                "admin_note": note or None, "is_read": False, "created_at": now(),
            }, session=tx)
        await write_audit_event(user["id"], f"poi.submission_{action}",
            f"submission:{sid}", ip,
            {"poi_id": str(submission.get("poi_id")), "fields": list(data), "dataset_version": version}, session=tx)
    return {"id": str(sid), "status": final_status,
            "poi_id": str(submission.get("poi_id")), "dataset_version": version}
