import time
import uuid
from typing import Optional
from app.core.database import get_db
from app.modules.mobile.schemas import ListeningHistoryCreate


class MobileHistoryService:
    @property
    def db(self):
        return get_db()

    async def save_listening_history(
        self, payload: ListeningHistoryCreate, user_id: Optional[str] = None
    ) -> dict:
        history_id = str(uuid.uuid4())
        poi_id = payload.stall_id or payload.poi_id or ""
        content_id = payload.stall_content_id or payload.poi_content_id or ""

        doc = {
            "_id": history_id,
            "poi_id": poi_id,
            "stall_id": poi_id,
            "poi_content_id": content_id,
            "stall_content_id": content_id,
            "user_id": user_id,
            "device_id": payload.device_id,
            "listened_at": payload.listened_at or int(time.time()),
            "listen_duration": payload.listen_duration,
            "created_at": int(time.time()),
        }
        await self.db.listening_histories.insert_one(doc)
        return {
            "id": history_id,
            "stall_id": poi_id,
            "poi_id": poi_id,
            "stall_content_id": content_id,
            "poi_content_id": content_id,
            "listened_at": doc["listened_at"],
            "listen_duration": doc["listen_duration"],
        }

    async def get_listening_history(
        self,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
        language: str = "vi",
    ) -> dict:
        query = {}
        if user_id:
            query["user_id"] = user_id
        elif device_id:
            query["device_id"] = device_id
        else:
            return {"total": 0, "items": []}

        cursor = self.db.listening_histories.find(query).sort("listened_at", -1)
        total = await self.db.listening_histories.count_documents(query)
        records = await cursor.skip(skip).limit(limit).to_list(length=limit)

        result_items = []
        for rec in records:
            poi_id = rec.get("stall_id") or rec.get("poi_id")
            content_id = rec.get("stall_content_id") or rec.get("poi_content_id")
            poi = await self.db.pois.find_one({"$or": [{"_id": poi_id}, {"id": poi_id}]}) or {}

            trans = (poi.get("translations") or {}).get(language) or {}
            poi_name = trans.get("name") or poi.get("name", "Quán ăn")
            cover_image = poi.get("cover_image") or (poi.get("images")[0] if poi.get("images") else None)

            result_items.append({
                "id": str(rec["_id"]),
                "stall_id": poi_id,
                "poi_id": poi_id,
                "stall_content_id": content_id,
                "poi_content_id": content_id,
                "listened_at": rec.get("listened_at", 0),
                "listen_duration": rec.get("listen_duration", 0),
                "stall_name": poi_name,
                "poi_name": poi_name,
                "cover_image": cover_image,
            })

        return {"total": total, "items": result_items}


mobile_history_service = MobileHistoryService()
