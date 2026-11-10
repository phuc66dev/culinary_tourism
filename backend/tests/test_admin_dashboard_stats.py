"""Dashboard Admin tính dữ liệu thật và không lộ thống kê cho Owner."""

from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import hash_password
from app.modules.analytics.service import LOCAL_TZ


async def test_admin_stats_empty_and_invalid_period(client, admin_creds):
    url = "/api/v1/admin/dashboard/stats"
    assert (await client.get(url)).status_code == 401
    assert (await client.post("/api/v1/admin/auth/login", json=admin_creds)).status_code == 200
    response = await client.get(url)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["days"] == 30
    assert body["summary"]["pois"] == {"total": 0, "active": 0, "inactive": 0}
    assert body["summary"]["registrations"]["pending"] == 0
    assert body["summary"]["users"]["total"] >= 1  # bootstrap Super Admin
    assert body["interactions"]["totals"]["views"] == 0
    assert len(body["interactions"]["daily"]) == 30
    assert not body["interactions"]["top_pois"]
    assert (await client.get(url, params={"days": 8})).status_code == 422


async def test_admin_dashboard_counts_trends_and_top_pois(client, admin_creds):
    db = get_db()
    today = datetime.now(LOCAL_TZ).date()
    yesterday = (today - timedelta(days=1)).isoformat()
    older = (today - timedelta(days=10)).isoformat()
    today_str = today.isoformat()

    poi_a = (await db["poi"].insert_one({"name": "Bánh tráng", "ward": "Phường 1", "is_active": True})).inserted_id
    poi_b = (await db["poi"].insert_one({"name": "Hủ tiếu", "ward": "Phường 2", "is_active": False})).inserted_id
    await db["poi"].insert_one({"name": "Quán chưa kích hoạt"})
    await db["poi_owner_registrations"].insert_many([
        {"status": "pending"}, {"status": "pending"}, {"status": "approved"}, {"status": "rejected"},
    ])
    await db["poi_submissions"].insert_many([{"status": "pending"}, {"status": "approved"}])
    await db["audio_tasks"].insert_many([
        {"status": "queued"}, {"status": "running"}, {"status": "paused"},
        {"status": "completed"}, {"status": "failed"}, {"status": "cancelled"},
    ])
    await db["users"].insert_one({"role": "poi_owner"})

    def analytics(poi_id, day, kind, language=None, seconds=None):
        return {
            "poi_id": poi_id, "day": day, "kind": kind,
            "language": language, "duration_seconds": seconds,
        }

    await db["analytics_poi_events"].insert_many([
        analytics(poi_a, today_str, "poi_viewed"),
        analytics(poi_a, today_str, "poi_viewed"),
        analytics(poi_a, yesterday, "search_poi_selected"),
        analytics(poi_a, today_str, "audio_started", "vi"),
        analytics(poi_a, today_str, "audio_completed", "vi", 20),
        analytics(poi_b, yesterday, "poi_viewed"),
        analytics(poi_b, yesterday, "audio_started", "en"),
        analytics(poi_b, yesterday, "audio_ended", "en", 7.5),
        analytics(poi_b, older, "poi_viewed"),
    ])

    assert (await client.post("/api/v1/admin/auth/login", json=admin_creds)).status_code == 200
    url = "/api/v1/admin/dashboard/stats"
    seven = (await client.get(url, params={"days": 7})).json()
    assert seven["summary"]["pois"] == {"total": 3, "active": 1, "inactive": 2}
    assert seven["summary"]["registrations"] == {"pending": 2, "approved": 1, "rejected": 1}
    assert seven["summary"]["submissions"] == {"pending": 1, "approved": 1, "rejected": 0}
    assert seven["summary"]["audio"]["processing"] == 3
    assert seven["summary"]["audio"]["failed"] == 1
    assert seven["summary"]["users"]["owners"] == 1
    assert seven["interactions"]["totals"] == {
        "views": 3, "search_selections": 1, "audio_starts": 2,
        "audio_completions": 1, "listen_seconds": 27.5,
    }
    assert len(seven["interactions"]["daily"]) == 7
    assert seven["interactions"]["daily"][-1]["views"] == 2
    assert seven["interactions"]["languages"] == [
        {"language": "en", "audio_starts": 1}, {"language": "vi", "audio_starts": 1},
    ]
    assert seven["interactions"]["top_pois"][0] == {
        "poi_id": str(poi_a), "name": "Bánh tráng", "ward": "Phường 1", "exists": True, "views": 2,
    }
    month = (await client.get(url, params={"days": 30})).json()
    assert month["interactions"]["totals"]["views"] == 4


async def test_owner_cannot_read_admin_stats(client):
    db = get_db()
    await db["users"].insert_one({
        "email": "stats-owner@example.com",
        "password_hash": hash_password("OwnerPassword123!"),
        "role": "poi_owner",
        "is_active": True,
    })
    assert (await client.post("/api/v1/admin/auth/login", json={
        "email": "stats-owner@example.com", "password": "OwnerPassword123!",
    })).status_code == 200
    assert (await client.get("/api/v1/admin/dashboard/stats")).status_code == 403
