"""AnalyticsService — Thu thập sự kiện ẩn danh khi người dùng đồng ý (Consent-gated)."""

from collections import Counter
from datetime import datetime, time, timedelta, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.core.database import get_db
from app.modules.analytics.schemas import AnalyticsBatch, TERMINAL_EVENTS

LOCAL_TZ = timezone(timedelta(hours=7))
RETENTION_DAYS = 90
COUNT_METRICS = {
    "poi_viewed": "views",
    "search_poi_selected": "search_selections",
    "audio_started": "audio_starts",
    "audio_completed": "audio_completions",
}
METRICS = (*COUNT_METRICS.values(), "listen_seconds")


class AnalyticsService:
    async def collect_event(self, payload: AnalyticsBatch) -> dict:
        db = get_db()
        now = datetime.now(LOCAL_TZ)
        candidate_ids = list({ObjectId(event.poi_id) for event in payload.events})
        active_ids = {
            poi["_id"]
            async for poi in db["poi"].find(
                {
                    "_id": {"$in": candidate_ids},
                    "$or": [{"is_active": True}, {"is_active": {"$exists": False}}],
                },
                {"_id": 1},
            )
        }

        recorded = 0
        oldest_day = now.date() - timedelta(days=RETENTION_DAYS - 1)
        earliest = datetime.combine(oldest_day, time.min, LOCAL_TZ)
        for event in payload.events:
            poi_id = ObjectId(event.poi_id)
            if poi_id not in active_ids or not earliest <= event.occurred_at <= now:
                continue
            day = event.occurred_at.astimezone(LOCAL_TZ).date()
            expires_at = datetime.combine(day + timedelta(days=RETENTION_DAYS), time.min, LOCAL_TZ)

            event_key = str(event.event_id)
            if event.playback_id is not None:
                phase = "end" if event.kind in TERMINAL_EVENTS else "start"
                event_key = f"{poi_id}:{event.playback_id}:{phase}"
            try:
                result = await db["analytics_poi_events"].update_one(
                    {"_id": event_key},
                    {"$setOnInsert": {
                        "poi_id": poi_id,
                        "day": day.isoformat(),
                        "kind": event.kind,
                        "language": event.language,
                        "duration_seconds": event.duration_seconds,
                        "expires_at": expires_at,
                    }},
                    upsert=True,
                )
            except DuplicateKeyError:
                continue
            recorded += int(result.upserted_id is not None)
        return {"status": "accepted", "recorded": recorded}

    async def get_poi_stats(self, poi_id: ObjectId, days: int) -> dict:
        today = datetime.now(LOCAL_TZ).date()
        first = today - timedelta(days=days - 1)
        daily = {
            (first + timedelta(days=offset)).isoformat(): dict.fromkeys(METRICS, 0)
            for offset in range(days)
        }
        languages = Counter()
        groups = get_db()["analytics_poi_events"].aggregate([
            {"$match": {"poi_id": poi_id, "day": {"$gte": first.isoformat(), "$lte": today.isoformat()}}},
            {"$group": {
                "_id": {"day": "$day", "kind": "$kind", "language": "$language"},
                "count": {"$sum": 1},
                "seconds": {"$sum": "$duration_seconds"},
            }},
        ])
        async for group in groups:
            day = daily[group["_id"]["day"]]
            kind = group["_id"]["kind"]
            if kind in COUNT_METRICS:
                day[COUNT_METRICS[kind]] += group["count"]
            day["listen_seconds"] += group["seconds"]
            if kind == "audio_started":
                languages[group["_id"]["language"]] += group["count"]

        return {
            "totals": {metric: sum(day[metric] for day in daily.values()) for metric in METRICS},
            "daily": [{"date": date, **metrics} for date, metrics in daily.items()],
            "languages": [
                {"language": language, "audio_starts": count}
                for language, count in sorted(languages.items(), key=lambda item: (-item[1], item[0]))
            ],
        }


analytics_service = AnalyticsService()
