"""Task-scoped manual translation escape hatch when the unofficial Google endpoint returns 429.

Only the queued, paused or failed job's remaining languages can be edited.
The first save pauses any queued retry. This prevents the background supervisor
from racing the Admin while entering translations. Admin explicitly resumes.
"""
from bson import ObjectId
from fastapi import HTTPException

from app.core.database import get_db, mongo_transaction
from app.modules.admin.audit import write_audit_event
from app.modules.audio.source_version import source_fingerprint
from app.modules.audio.task_store import audio_task_store, now

LANGS = frozenset(("en", "zh", "ja", "ko"))


async def save_task_manual_translation(
    task_id: str, lang: str, title: str, description: str,
    actor_id: str, actor_ip: str | None = None,
) -> dict:
    if not ObjectId.is_valid(task_id):
        raise HTTPException(400, "Mã tác vụ không hợp lệ")
    if lang not in LANGS:
        raise HTTPException(422, "Chỉ được nhập bản dịch Anh, Trung, Nhật, Hàn")
    title = title.strip()
    description = description.strip()
    if not title or not description:
        raise HTTPException(422, "Cần nhập cả tên và mô tả đã dịch")

    db = get_db()
    stamp = now()
    async with mongo_transaction() as tx:
        task = await db["audio_tasks"].find_one({"_id": ObjectId(task_id)}, session=tx)
        if not task:
            raise HTTPException(404, "Không tìm thấy tác vụ")
        if task.get("status") not in ("queued", "paused", "failed"):
            raise HTTPException(409, "Hãy tạm dừng tác vụ đang chạy trước khi nhập bản dịch")
        if task["status"] == "failed":
            other = await db["audio_tasks"].find_one(
                {"_id": {"$ne": ObjectId(task_id)}, "poi_id": task.get("poi_id"),
                 "status": {"$in": ["queued", "running", "paused"]}},
                {"_id": 1}, session=tx,
            )
            if other:
                raise HTTPException(409, "Quán đang có tác vụ audio mới; không thể sửa tác vụ lỗi cũ")
        langs = task.get("languages") or []
        if lang not in langs or langs.index(lang) < int(task.get("done", 0)):
            raise HTTPException(409, "Ngôn ngữ này đã hoàn tất hoặc không thuộc tác vụ")
        if not ObjectId.is_valid(str(task.get("poi_id"))):
            raise HTTPException(409, "Tác vụ có mã POI không hợp lệ")
        poi_id = ObjectId(str(task["poi_id"]))
        poi = await db["poi"].find_one({"_id": poi_id}, session=tx)
        if not poi:
            raise HTTPException(404, "Quán ăn không còn tồn tại")
        base = (poi.get("original_description") or poi.get("description") or "").strip()
        if not base:
            vi = await db["poi_localizations"].find_one(
                {"poi_id": poi_id, "lang": "vi"}, session=tx)
            base = str((vi or {}).get("description") or "").strip()
        fingerprint = source_fingerprint(poi.get("name") or "", base)
        if not task.get("source_hash") and int(task.get("done", 0)) > 0:
            raise HTTPException(409, "Tác vụ cũ thiếu phiên bản nguồn; hãy hủy và tạo tác vụ mới")
        if task.get("source_hash") and task["source_hash"] != fingerprint:
            raise HTTPException(409, "Mô tả gốc đã đổi; cần tạo tác vụ mới")
        if poi.get("is_active") and lang == "en":
            raise HTTPException(409, "Hãy ẩn quán trước khi sửa bản dịch tiếng Anh")

        # Pausing the retry atomically with the translation write avoids a race
        # with the supervisor claiming a due queued task on another API worker.
        changed = await db["audio_tasks"].update_one(
            {"_id": ObjectId(task_id), "status": task["status"]},
            {"$set": {"status": "paused", "error": None, "source_hash": fingerprint,
                      "current_language": None, "updated_at": stamp},
             "$unset": {"retry_at": "", "finished_at": ""}}, session=tx,
        )
        if not changed.matched_count:
            raise HTTPException(409, "Trạng thái tác vụ đã đổi; vui lòng tải lại")
        await db["poi_localizations"].update_one(
            {"poi_id": poi_id, "lang": lang},
            {"$set": {"title": title, "description": description,
                      "source_hash": fingerprint, "translation_origin": "manual",
                      "audio_status": "pending", "audio_url": None,
                      "is_fallback": False, "updated_at": stamp},
             "$setOnInsert": {"created_at": stamp}},
            upsert=True, session=tx,
        )
        await db["system_meta"].update_one(
            {"_id": "dataset"},
            {"$inc": {"version": 1}, "$set": {"updated_at": stamp}},
            upsert=True, session=tx,
        )
        await write_audit_event(
            actor_id, "audio.manual_translation", f"audio_task:{task_id}", actor_ip,
            {"poi_id": str(poi_id), "language": lang, "mode": "manual"}, session=tx,
        )
    audio_task_store._notify()
    return {"status": "paused", "lang": lang, "message": "Đã lưu bản dịch. Nhập tiếp hoặc nhấn Resume."}
