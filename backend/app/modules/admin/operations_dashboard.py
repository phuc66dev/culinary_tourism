"""Operational Admin dashboard. Uses authoritative collections, no seeded/demo figures.

Snapshot metrics are independent of the selected interaction time window. The
48-hour aging threshold is a *monitoring hint*, not a business SLA.
"""

import asyncio
from datetime import datetime, time, timedelta, timezone

from app.core.database import get_db
from app.modules.admin.dashboard_stats import get_admin_dashboard_stats
from app.modules.admin.poi_management import localized_ready
from app.modules.analytics.service import LOCAL_TZ


async def _readiness_snapshot(db, *, batch_size: int = 250) -> dict:
    """Use the exact POI publication gate, reading only a bounded POI batch.

    A POI can be public while failing the gate if legacy data was edited outside
    the application. We surface this as a data-quality warning, not as ready.
    """
    counters = {
        "total": 0,
        "published": 0,
        "ready": 0,
        "ready_unpublished": 0,
        "blocked_unpublished": 0,
        "published_not_ready": 0,
        "missing_english_content": 0,
        "missing_english_audio": 0,
        "linked_to_owner": 0,
    }

    async def process(pois: list[dict]) -> None:
        ids = [poi["_id"] for poi in pois]
        english = {
            doc["poi_id"]: doc
            async for doc in db["poi_localizations"].find(
                {"poi_id": {"$in": ids}, "lang": "en"},
                {"poi_id": 1, "title": 1, "description": 1, "audio_status": 1, "audio_url": 1},
            )
        }
        for poi in pois:
            counters["total"] += 1
            published = poi.get("is_active") is True
            en = english.get(poi["_id"])
            gate = localized_ready(en)
            ready = gate["ready"]
            if published:
                counters["published"] += 1
            if ready:
                counters["ready"] += 1
            if published and not ready:
                counters["published_not_ready"] += 1
            if not published:
                counters["ready_unpublished" if ready else "blocked_unpublished"] += 1
            if not en or not str(en.get("title") or "").strip() or not str(en.get("description") or "").strip():
                counters["missing_english_content"] += 1
            if not en or en.get("audio_status") != "completed" or not str(en.get("audio_url") or "").strip():
                counters["missing_english_audio"] += 1
            if poi.get("owner_id"):
                counters["linked_to_owner"] += 1

    batch = []
    async for poi in db["poi"].find({}, {"_id": 1, "is_active": 1, "owner_id": 1}):
        batch.append(poi)
        if len(batch) == batch_size:
            await process(batch)
            batch = []
    if batch:
        await process(batch)
    return counters


async def _aging_snapshot(db, now: datetime) -> dict:
    """Backlog older than 48h based on creation timestamp (UTC storage)."""
    cutoff = now - timedelta(hours=48)
    registrations, submissions = await asyncio.gather(
        db["poi_owner_registrations"].count_documents({"status": "pending", "created_at": {"$lt": cutoff}}),
        db["poi_submissions"].count_documents({"status": "pending", "created_at": {"$lt": cutoff}}),
    )
    return {"threshold_hours": 48, "registrations": registrations, "submissions": submissions}


def _utc_aware(value):
    """MongoDB returns naive UTC datetimes by default."""
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


async def _review_performance(db, days: int, now: datetime) -> dict:
    """Completed decisions in the chosen Vietnam-local calendar window.

    Uses the actual reviewed_at timestamp of each registration/submission.
    No personal information is selected or returned.
    """
    first_day = now.astimezone(LOCAL_TZ).date() - timedelta(days=days - 1)
    first_utc = datetime.combine(first_day, time.min, tzinfo=LOCAL_TZ).astimezone(timezone.utc)

    async def counts(collection) -> tuple[dict, float, int]:
        approved = rejected = 0
        duration_hours = 0.0
        timed_count = 0
        async for doc in collection.find(
            {"status": {"$in": ["approved", "rejected"]},
             "reviewed_at": {"$gte": first_utc, "$lte": now}},
            {"_id": 0, "status": 1, "created_at": 1, "reviewed_at": 1},
        ):
            if doc.get("status") == "approved":
                approved += 1
            else:
                rejected += 1
            created = _utc_aware(doc.get("created_at"))
            reviewed = _utc_aware(doc.get("reviewed_at"))
            if created and reviewed and reviewed >= created:
                duration_hours += (reviewed - created).total_seconds() / 3600
                timed_count += 1
        total = approved + rejected
        return ({
            "processed": total,
            "approved": approved,
            "rejected": rejected,
            "approval_rate_percent": round(approved * 100 / total, 1) if total else None,
            "average_review_hours": round(duration_hours / timed_count, 1) if timed_count else None,
        }, duration_hours, timed_count)

    registrations, submissions = await asyncio.gather(
        counts(db["poi_owner_registrations"]),
        counts(db["poi_submissions"]),
    )
    a, b = registrations[0], submissions[0]
    total = a["processed"] + b["processed"]
    hours = registrations[1] + submissions[1]
    timed_count = registrations[2] + submissions[2]
    return {
        "days": days,
        "processed": total,
        "approved": a["approved"] + b["approved"],
        "rejected": a["rejected"] + b["rejected"],
        "average_review_hours": round(hours / timed_count, 1) if timed_count else None,
        "registrations": a,
        "submissions": b,
    }


async def get_operations_dashboard(days: int = 30) -> dict:
    """Main endpoint payload: current operations + consented interaction events."""
    if days not in (7, 30, 90):
        raise ValueError("days must be 7, 30 or 90")
    db = get_db()
    now = datetime.now(timezone.utc)
    base, readiness, aging, review_performance = await asyncio.gather(
        get_admin_dashboard_stats(days),
        _readiness_snapshot(db),
        _aging_snapshot(db, now),
        _review_performance(db, days, now),
    )
    base["operations"] = {
        "poi_readiness": readiness,
        "pending_over_48h": aging,
        "review_performance": review_performance,
        # Never present this percentage as a conversion or readiness trend.
        "publication_rate_percent": round(100 * readiness["published"] / readiness["total"], 1)
        if readiness["total"] else None,
        "readiness_rate_percent": round(100 * readiness["ready"] / readiness["total"], 1)
        if readiness["total"] else None,
    }
    return base
