import math
import re
from typing import Dict, List, Optional, Tuple
from bson import ObjectId
from fastapi import HTTPException
from app.core.database import get_db
from app.modules.mobile.utils.i18n import t


class MobilePoiService:
    @property
    def db(self):
        return get_db()

    @property
    def poi_coll(self):
        """Ưu tiên collection chuẩn `poi` (số ít). Nếu chưa có thì fallback sang `pois`."""
        return self.db["poi"]

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Công thức Haversine tính khoảng cách (km)."""
        R = 6371.0
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(d_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 2)

    async def _find_poi(self, poi_id: str) -> Optional[dict]:
        """Tìm quán ăn theo _id (ObjectId hoặc str), slug hoặc id trong cả collection `poi` và fallback `pois`."""
        query_conditions = [{"_id": poi_id}, {"id": poi_id}, {"slug": poi_id}]
        if ObjectId.is_valid(poi_id):
            query_conditions.append({"_id": ObjectId(poi_id)})

        # 1. Tìm trong collection chuẩn `poi`
        poi = await self.db["poi"].find_one({"$or": query_conditions})
        if poi:
            return poi

        # 2. Fallback sang `pois` nếu hệ thống cũ còn lưu
        return await self.db["pois"].find_one({"$or": query_conditions})

    async def get_listened_poi_ids(self, user_id: Optional[str] = None, device_id: Optional[str] = None) -> set:
        """Lấy danh sách ID các quán người dùng hoặc thiết bị này đã từng nghe."""
        query = {}
        if user_id:
            query = {"user_id": user_id}
        elif device_id:
            query = {"device_id": device_id}
        else:
            return set()

        cursor = self.db.listening_histories.find(query, {"poi_id": 1, "stall_id": 1})
        histories = await cursor.to_list(length=1000)
        result = set()
        for h in histories:
            pid = h.get("poi_id") or h.get("stall_id")
            if pid:
                result.add(str(pid))
        return result

    async def get_pois(
        self,
        keyword: Optional[str] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        limit: int = 20,
        offset: int = 0,
        language: str = "vi",
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> Tuple[List[dict], int]:
        filter_query: dict = {"$or": [{"is_active": True}, {"is_active": {"$exists": False}}]}

        if keyword:
            kw = keyword.strip()
            filter_query["$and"] = [
                {
                    "$or": [
                        {"name": {"$regex": re.escape(kw), "$options": "i"}},
                        {"category": {"$regex": re.escape(kw), "$options": "i"}},
                        {"address": {"$regex": re.escape(kw), "$options": "i"}},
                        {"original_description": {"$regex": re.escape(kw), "$options": "i"}},
                        {f"translations.{language}.name": {"$regex": re.escape(kw), "$options": "i"}},
                    ]
                }
            ]

        # Truy vấn từ collection chuẩn `poi`, fallback sang `pois` nếu `poi` chưa có dữ liệu
        cursor = self.db["poi"].find(filter_query)
        all_pois = await cursor.to_list(length=500)
        if not all_pois:
            cursor_fallback = self.db["pois"].find(filter_query)
            all_pois = await cursor_fallback.to_list(length=500)

        total = len(all_pois)
        listened_ids = await self.get_listened_poi_ids(user_id=user_id, device_id=device_id)

        items = []
        for poi in all_pois:
            raw_id = poi.get("_id")
            poi_id = str(raw_id) if raw_id is not None else str(poi.get("id", ""))
            
            # Trích xuất tọa độ từ GeoJSON hoặc latitude/longitude trực tiếp
            loc = poi.get("location")
            if isinstance(loc, dict) and "coordinates" in loc and len(loc["coordinates"]) >= 2:
                poi_lng, poi_lat = float(loc["coordinates"][0]), float(loc["coordinates"][1])
            else:
                poi_lat = float(poi.get("latitude", 10.758))
                poi_lng = float(poi.get("longitude", 106.702))

            # Tên và bản dịch theo ngôn ngữ yêu cầu
            poi_name = poi.get("name", "")
            category = poi.get("category", "street_food")
            
            if language != "vi":
                # Tìm bản dịch trong poi_localizations
                loc_doc = await self.db["poi_localizations"].find_one({
                    "poi_id": {"$in": [raw_id, poi_id]},
                    "lang": language
                })
                if loc_doc and loc_doc.get("title"):
                    poi_name = loc_doc["title"]
                elif poi.get("translations", {}).get(language, {}).get("name"):
                    poi_name = poi["translations"][language]["name"]

            # Khoảng cách GPS
            distance = None
            if lat is not None and lng is not None:
                distance = self._calculate_distance(lat, lng, poi_lat, poi_lng)

            is_listened = poi_id in listened_ids or str(raw_id) in listened_ids

            items.append({
                "id": poi_id,
                "name": poi_name,
                "latitude": poi_lat,
                "longitude": poi_lng,
                "radius": int(poi.get("trigger_radius", poi.get("radius", 30))),
                "priority": int(poi.get("audio_priority", poi.get("priority", 5))),
                "is_listened": is_listened,
                "cover_image": poi.get("cover_image") or (poi.get("images")[0] if poi.get("images") else None),
                "images": poi.get("images", []),
                "address": poi.get("address", ""),
                "category": category,
                "price_range": poi.get("price_range"),
                "opening_hours": poi.get("opening_hours"),
                "close_hours": poi.get("close_hours"),
                "contact_phone": poi.get("contact_phone"),
                "website": poi.get("website"),
                "average_rating": float(poi.get("average_rating", 0.0)),
                "total_reviews": int(poi.get("total_reviews", 0)),
                "distance": distance,
                "created_at": poi.get("created_at", 0),
            })

        # Sắp xếp thông minh:
        # 1. Có tọa độ: Chưa nghe lên trước -> Gần nhất lên trước -> Priority cao lên trước
        # 2. Không có tọa độ: Mới tạo lên trước
        if lat is not None and lng is not None:
            items.sort(key=lambda x: (
                1 if x["is_listened"] else 0,
                x["distance"] if x["distance"] is not None else 999999,
                -x["priority"],
            ))
        else:
            items.sort(key=lambda x: -x["created_at"] if isinstance(x["created_at"], (int, float)) else 0)

        paginated_items = items[offset : offset + limit]
        return paginated_items, total

    async def get_poi_by_id(
        self,
        poi_id: str,
        language: str = "vi",
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> Optional[dict]:
        poi = await self._find_poi(poi_id)
        if not poi:
            return None

        raw_id = poi.get("_id")
        clean_id = str(raw_id) if raw_id is not None else str(poi.get("id", poi_id))

        loc = poi.get("location")
        if isinstance(loc, dict) and "coordinates" in loc and len(loc["coordinates"]) >= 2:
            poi_lng, poi_lat = float(loc["coordinates"][0]), float(loc["coordinates"][1])
        else:
            poi_lat = float(poi.get("latitude", 10.758))
            poi_lng = float(poi.get("longitude", 106.702))

        poi_name = poi.get("name", "")
        category = poi.get("category", "street_food")
        description = poi.get("original_description", "")

        if language != "vi":
            loc_doc = await self.db["poi_localizations"].find_one({
                "poi_id": {"$in": [raw_id, clean_id]},
                "lang": language
            })
            if loc_doc:
                if loc_doc.get("title"):
                    poi_name = loc_doc["title"]
                if loc_doc.get("description"):
                    description = loc_doc["description"]
            elif poi.get("translations", {}).get(language):
                trans = poi["translations"][language]
                poi_name = trans.get("name") or poi_name
                category = trans.get("category") or category

        listened_ids = await self.get_listened_poi_ids(user_id=user_id, device_id=device_id)

        return {
            "id": clean_id,
            "name": poi_name,
            "latitude": poi_lat,
            "longitude": poi_lng,
            "radius": int(poi.get("trigger_radius", poi.get("radius", 30))),
            "priority": int(poi.get("audio_priority", poi.get("priority", 5))),
            "is_listened": clean_id in listened_ids or str(raw_id) in listened_ids,
            "cover_image": poi.get("cover_image") or (poi.get("images")[0] if poi.get("images") else None),
            "images": poi.get("images", []),
            "address": poi.get("address", ""),
            "description": description,
            "category": category,
            "price_range": poi.get("price_range"),
            "opening_hours": poi.get("opening_hours"),
            "close_hours": poi.get("close_hours"),
            "contact_phone": poi.get("contact_phone"),
            "website": poi.get("website"),
            "average_rating": float(poi.get("average_rating", 0.0)),
            "total_reviews": int(poi.get("total_reviews", 0)),
            "distance": None,
        }

    async def get_content_with_fallback(self, poi_id: str, language: str) -> List[Dict]:
        """Lấy bài thuyết minh có cơ chế 3-tier fallback."""
        poi = await self._find_poi(poi_id)
        if not poi:
            return []

        raw_id = poi.get("_id")
        clean_id = str(raw_id) if raw_id is not None else poi_id

        translations = poi.get("translations") or {}
        is_fallback = False
        target_trans = None
        target_lang = language

        # 1. Tìm bản dịch trong collection chuẩn `poi_localizations`
        loc_target = await self.db["poi_localizations"].find_one({
            "poi_id": {"$in": [raw_id, clean_id]},
            "lang": language,
            "audio_status": "completed",
        })

        if loc_target:
            target_trans = {
                "name": loc_target.get("title") or poi.get("name", ""),
                "tts_script": loc_target.get("description") or poi.get("original_description", ""),
                "audio_url": loc_target.get("audio_url"),
                "audio_duration": loc_target.get("duration", 0),
            }
        elif language in translations:
            target_trans = translations[language]
        else:
            # Tier 2: Dự phòng tiếng Việt
            loc_vi = await self.db["poi_localizations"].find_one({
                "poi_id": {"$in": [raw_id, clean_id]},
                "lang": "vi",
            })
            if loc_vi:
                target_trans = {
                    "name": loc_vi.get("title") or poi.get("name", ""),
                    "tts_script": loc_vi.get("description") or poi.get("original_description", ""),
                    "audio_url": loc_vi.get("audio_url"),
                    "audio_duration": loc_vi.get("duration", 0),
                }
                target_lang = "vi"
                is_fallback = True
            elif "vi" in translations:
                target_trans = translations["vi"]
                target_lang = "vi"
                is_fallback = True
            elif translations:
                first_lang = next(iter(translations))
                target_trans = translations[first_lang]
                target_lang = first_lang
                is_fallback = True

        title = target_trans.get("name") if target_trans else poi.get("name", "")
        text_content = target_trans.get("tts_script") if target_trans else poi.get("original_description", "")
        audio_url = target_trans.get("audio_url") if target_trans else poi.get("audio_url")
        duration = target_trans.get("audio_duration") if target_trans else poi.get("audio_duration", 0)

        response = {
            "id": f"content_{clean_id}",
            "stall_id": clean_id,
            "poi_id": clean_id,
            "language_code": target_lang,
            "title": title,
            "text_content": text_content,
            "translated_text": text_content,
            "audio_url": audio_url,
            "duration": duration,
            "order": 1,
            "is_fallback": is_fallback,
        }
        return [response]

    async def get_available_languages(self, poi_id: str) -> List[Dict]:
        poi = await self._find_poi(poi_id)
        if not poi:
            return []

        raw_id = poi.get("_id")
        clean_id = str(raw_id) if raw_id is not None else poi_id

        languages_set = set()

        # Đọc từ collection chuẩn `poi_localizations`
        loc_langs = await self.db["poi_localizations"].distinct(
            "lang", {"poi_id": {"$in": [raw_id, clean_id]}}
        )
        for l in loc_langs:
            if l:
                languages_set.add(l)

        # Đọc từ trường translations (nếu có)
        translations = poi.get("translations") or {}
        for l in translations.keys():
            if l:
                languages_set.add(l)

        if not languages_set:
            languages_set.add("vi")

        return [{"language_code": code} for code in sorted(languages_set)]

    async def get_nearby_content(
        self,
        lat: float,
        lng: float,
        radius: float = 30.0,
        language: str = "vi",
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[dict]:
        """
        Lấy danh sách các bài thuyết minh audio của các POI nằm trong vùng phát tự động (Geofence),
        sắp xếp các POI gần nhau theo thứ tự khoảng cách tăng dần (ưu tiên gần nhất phát trước).
        """
        filter_query: dict = {"$or": [{"is_active": True}, {"is_active": {"$exists": False}}]}

        cursor = self.db["poi"].find(filter_query)
        all_pois = await cursor.to_list(length=500)
        if not all_pois:
            cursor_fallback = self.db["pois"].find(filter_query)
            all_pois = await cursor_fallback.to_list(length=500)

        listened_ids = await self.get_listened_poi_ids(user_id=user_id, device_id=device_id)

        matched_pois = []
        for poi in all_pois:
            raw_id = poi.get("_id")
            poi_id = str(raw_id) if raw_id is not None else str(poi.get("id", ""))

            # Trích xuất tọa độ từ GeoJSON hoặc trường latitude/longitude
            loc = poi.get("location")
            if isinstance(loc, dict) and "coordinates" in loc and len(loc["coordinates"]) >= 2:
                poi_lng, poi_lat = float(loc["coordinates"][0]), float(loc["coordinates"][1])
            else:
                poi_lat = float(poi.get("latitude", 10.758))
                poi_lng = float(poi.get("longitude", 106.702))

            # Khoảng cách mét = km * 1000
            distance_meters = self._calculate_distance(lat, lng, poi_lat, poi_lng) * 1000.0

            # Bán kính Geofence của quán (trigger_radius hoặc radius, fallback radius truyền vào)
            effective_radius = float(poi.get("trigger_radius", poi.get("radius", radius)))

            if distance_meters <= effective_radius:
                is_listened = poi_id in listened_ids or str(raw_id) in listened_ids
                priority = int(poi.get("audio_priority", poi.get("priority", 5)))
                matched_pois.append({
                    "poi": poi,
                    "poi_id": poi_id,
                    "distance_meters": round(distance_meters, 1),
                    "is_listened": is_listened,
                    "priority": priority,
                })

        # Sắp xếp các quán gần nhau:
        # 1. Chưa nghe lên trước
        # 2. Khoảng cách gần nhất lên trước
        # 3. Audio priority cao lên trước
        matched_pois.sort(key=lambda x: (
            1 if x["is_listened"] else 0,
            x["distance_meters"],
            -x["priority"],
        ))

        # Giới hạn số lượng quán
        matched_pois = matched_pois[:limit]

        # Lấy nội dung thuyết minh kèm đa ngôn ngữ cho từng POI
        results = []
        for item in matched_pois:
            poi = item["poi"]
            poi_id = item["poi_id"]
            dist = item["distance_meters"]
            cover_image = poi.get("cover_image") or (poi.get("images")[0] if poi.get("images") else None)

            contents = await self.get_content_with_fallback(poi_id, language=language)
            for c in contents:
                entry = dict(c)
                entry["stall_name"] = entry.get("title") or poi.get("name", "")
                entry["poi_name"] = entry.get("title") or poi.get("name", "")
                entry["distance_meters"] = dist
                entry["cover_image"] = cover_image
                results.append(entry)

        return results


mobile_poi_service = MobilePoiService()
