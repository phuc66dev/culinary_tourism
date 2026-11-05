import math
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException
from app.core.database import get_db
from app.modules.mobile.utils.i18n import t


class MobilePoiService:
    @property
    def db(self):
        return get_db()

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

    async def get_listened_poi_ids(self, user_id: Optional[str] = None, device_id: Optional[str] = None) -> set:
        """Lấy danh sách ID các quán người dùng hoặc thiết bị này đã từng nghe."""
        query = {}
        if user_id:
            query = {"user_id": user_id}
        elif device_id:
            query = {"device_id": device_id}
        else:
            return set()

        cursor = self.db.listening_histories.find(query, {"poi_id": 1})
        histories = await cursor.to_list(length=1000)
        return {h["poi_id"] for h in histories if "poi_id" in h}

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
                        {"name": {"$regex": kw, "$options": "i"}},
                        {"category": {"$regex": kw, "$options": "i"}},
                        {f"translations.{language}.name": {"$regex": kw, "$options": "i"}},
                    ]
                }
            ]

        cursor = self.db.pois.find(filter_query)
        all_pois = await cursor.to_list(length=500)
        total = len(all_pois)

        listened_ids = await self.get_listened_poi_ids(user_id=user_id, device_id=device_id)

        items = []
        for poi in all_pois:
            poi_id = str(poi.get("_id", poi.get("id", "")))
            # Trích xuất tọa độ từ GeoJSON hoặc float trực tiếp
            loc = poi.get("location")
            if isinstance(loc, dict) and "coordinates" in loc:
                poi_lng, poi_lat = loc["coordinates"][0], loc["coordinates"][1]
            else:
                poi_lat = float(poi.get("latitude", 10.758))
                poi_lng = float(poi.get("longitude", 106.702))

            # Bản dịch
            trans = (poi.get("translations") or {}).get(language) or {}
            poi_name = trans.get("name") or poi.get("name", "")

            # Khoảng cách
            distance = None
            if lat is not None and lng is not None:
                distance = self._calculate_distance(lat, lng, poi_lat, poi_lng)

            is_listened = poi_id in listened_ids

            items.append({
                "id": poi_id,
                "name": poi_name,
                "latitude": poi_lat,
                "longitude": poi_lng,
                "radius": int(poi.get("trigger_radius", poi.get("radius", 30))),
                "priority": int(poi.get("audio_priority", poi.get("priority", 0))),
                "is_listened": is_listened,
                "cover_image": poi.get("cover_image") or (poi.get("images")[0] if poi.get("images") else None),
                "category": trans.get("category") or poi.get("category", "street_food"),
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
        # 1. Có tọa độ: Ưu tiên khoảng cách gần nhất -> Quán chưa nghe lên trước -> Priority cao lên trước
        # 2. Không có tọa độ: Mới tạo lên trước
        if lat is not None and lng is not None:
            items.sort(key=lambda x: (
                1 if x["is_listened"] else 0,   # Chưa nghe trước (0), đã nghe sau (1)
                x["distance"] if x["distance"] is not None else 999999,  # Gần lên trước
                -x["priority"],                 # Ưu tiên cao lên trước
            ))
        else:
            items.sort(key=lambda x: -x["created_at"])

        paginated_items = items[offset : offset + limit]
        return paginated_items, total

    async def get_poi_by_id(
        self,
        poi_id: str,
        language: str = "vi",
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> Optional[dict]:
        poi = await self.db.pois.find_one({"$or": [{"_id": poi_id}, {"id": poi_id}]})
        if not poi:
            return None

        loc = poi.get("location")
        if isinstance(loc, dict) and "coordinates" in loc:
            poi_lng, poi_lat = loc["coordinates"][0], loc["coordinates"][1]
        else:
            poi_lat = float(poi.get("latitude", 10.758))
            poi_lng = float(poi.get("longitude", 106.702))

        trans = (poi.get("translations") or {}).get(language) or {}
        listened_ids = await self.get_listened_poi_ids(user_id=user_id, device_id=device_id)

        return {
            "id": poi_id,
            "name": trans.get("name") or poi.get("name", ""),
            "latitude": poi_lat,
            "longitude": poi_lng,
            "radius": int(poi.get("trigger_radius", poi.get("radius", 30))),
            "priority": int(poi.get("audio_priority", poi.get("priority", 0))),
            "is_listened": poi_id in listened_ids,
            "cover_image": poi.get("cover_image") or (poi.get("images")[0] if poi.get("images") else None),
            "category": trans.get("category") or poi.get("category", "street_food"),
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
        poi = await self.db.pois.find_one({"$or": [{"_id": poi_id}, {"id": poi_id}]})
        if not poi:
            return []

        translations = poi.get("translations") or {}
        is_fallback = False
        target_trans = None
        target_lang = language

        # Tier 1: Ngôn ngữ khách yêu cầu
        if language in translations:
            target_trans = translations[language]
        # Tier 2: Dự phòng tiếng Việt
        elif "vi" in translations:
            target_trans = translations["vi"]
            target_lang = "vi"
            is_fallback = True
        # Tier 3: Bất kỳ ngôn ngữ nào có sẵn
        elif translations:
            first_lang = next(iter(translations))
            target_trans = translations[first_lang]
            target_lang = first_lang
            is_fallback = True

        title = target_trans.get("name") if target_trans else poi.get("name", "")
        text_content = target_trans.get("tts_script") if target_trans else poi.get("original_description")
        audio_url = target_trans.get("audio_url") if target_trans else poi.get("audio_url")
        duration = target_trans.get("audio_duration") if target_trans else poi.get("audio_duration", 0)

        response = {
            "id": f"content_{poi_id}",
            "stall_id": poi_id,
            "poi_id": poi_id,
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
        poi = await self.db.pois.find_one({"$or": [{"_id": poi_id}, {"id": poi_id}]})
        if not poi:
            return []
        translations = poi.get("translations") or {}
        return [{"language_code": code} for code in translations.keys()]


mobile_poi_service = MobilePoiService()

