"""Số liệu tổng quan dành cho Admin, tổng hợp trực tiếp từ MongoDB.

Không trả về dữ liệu cá nhân; sự kiện tương tác là những sự kiện đã được
người dùng đồng ý ghi nhận qua /analytics/collect (tối đa 90 ngày).
"""

import asyncio
from collections import Counter
from datetime import datetime, timedelta

from bson import ObjectId

from app.core.database import get_db
from app.modules.analytics.service import COUNT_METRICS, LOCAL_TZ, METRICS, RETENTION_DAYS

REVIEW_STATUSES = ("pending", "approved", "rejected")
AUDIO_STATUSES = ("queued", "running", "paused", "completed", "failed", "cancelled")


async def _status_breakdown(collection, statuses: tuple[str, ...]) -> dict:
    """Một aggregation cho mọi trạng thái, không phân trang/bỏ sót bản ghi."""
    counts = dict.fromkeys(statuses, 0)
    async for row in collection.aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]):
        if row["_id"] in counts:
            counts[row["_id"]] = row["count"]
    return counts


async def get_admin_dashboard_stats(days: int = 30) -> dict:
    """Số liệu toàn hệ thống. Route phải bảo vệ bằng quyền analytics:view."""
    if days not in (7, 30, 90):
        raise ValueError("days must be 7, 30 or 90")

    db = get_db()
    today = datetime.now(LOCAL_TZ).date()
    first = today - timedelta(days=days - 1)
    date_match = {"$gte": first.isoformat(), "$lte": today.isoformat()}

    (
        poi_total,
        poi_active,
        users_total,
        owners_total,
        registrations,
        submissions,
        audio,
    ) = await asyncio.gather(
        db["poi"].count_documents({}),
        db["poi"].count_documents({"is_active": True}),
        db["users"].count_documents({}),
        db["users"].count_documents({"role": "poi_owner"}),
        _status_breakdown(db["poi_owner_registrations"], REVIEW_STATUSES),
        _status_breakdown(db["poi_submissions"], REVIEW_STATUSES),
        _status_breakdown(db["audio_tasks"], AUDIO_STATUSES),
    )

    daily = {
        (first + timedelta(days=offset)).isoformat(): dict.fromkeys(METRICS, 0)
        for offset in range(days)
    }
    languages = Counter()
    # Dùng chính định nghĩa metric đã áp dụng cho thống kê chủ quán để số liệu nhất quán.
    async for group in db["analytics_poi_events"].aggregate([
        {"$match": {"day": date_match}},
        {"$group": {
            "_id": {"day": "$day", "kind": "$kind", "language": "$language"},
            "count": {"$sum": 1},
            "seconds": {"$sum": "$duration_seconds"},
        }},
    ]):
        info = group["_id"]
        day = daily.get(info["day"])
        if day is None:
            continue
        kind = info["kind"]
        if kind in COUNT_METRICS:
            day[COUNT_METRICS[kind]] += group["count"]
        if kind in ("audio_completed", "audio_ended"):
            day["listen_seconds"] += group.get("seconds") or 0
        if kind == "audio_started" and info.get("language"):
            languages[info["language"]] += group["count"]

    # Chỉ xếp hạng lượt xem chi tiết; tránh tính nhầm lượt nghe và lượt chọn tìm kiếm.
    top_counts = [row async for row in db["analytics_poi_events"].aggregate([
        {"$match": {"day": date_match, "kind": "poi_viewed"}},
        {"$group": {"_id": "$poi_id", "views": {"$sum": 1}}},
        {"$sort": {"views": -1, "_id": 1}},
        {"$limit": 5},
    ])]
    ids = [ObjectId(str(row["_id"])) for row in top_counts if ObjectId.is_valid(str(row["_id"]))]
    poi_names = {
        str(doc["_id"]): doc
        async for doc in db["poi"].find({"_id": {"$in": ids}}, {"name": 1, "ward": 1})
    } if ids else {}
    top_pois = []
    for row in top_counts:
        poi_id = str(row["_id"])
        poi = poi_names.get(poi_id)
        top_pois.append({
            "poi_id": poi_id,
            "name": (poi or {}).get("name") or "Địa điểm không còn tồn tại",
            "ward": (poi or {}).get("ward"),
            "exists": poi is not None,
            "views": row["views"],
        })

    return {
        "days": days,
        "generated_at": datetime.now(LOCAL_TZ).isoformat(),
        "summary": {
            "pois": {"total": poi_total, "active": poi_active, "inactive": poi_total - poi_active},
            "users": {"total": users_total, "owners": owners_total},
            "registrations": registrations,
            "submissions": submissions,
            "audio": {
                **audio,
                "processing": sum(audio[status] for status in ("queued", "running", "paused")),
            },
        },
        "interactions": {
            "totals": {metric: sum(day[metric] for day in daily.values()) for metric in METRICS},
            "daily": [{"date": date, **metrics} for date, metrics in daily.items()],
            "languages": [
                {"language": language, "audio_starts": count}
                for language, count in sorted(languages.items(), key=lambda item: (-item[1], item[0]))
            ],
            "top_pois": top_pois,
        },
        "retention_days": RETENTION_DAYS,
    }
