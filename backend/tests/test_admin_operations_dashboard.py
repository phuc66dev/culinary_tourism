"""Dashboard operational KPIs against isolated mongomock Motor DB."""

from datetime import datetime, timedelta, timezone

from app.core.database import get_db


async def test_operational_dashboard_empty_and_ranges(client, admin_creds):
    url = "/api/v1/admin/dashboard/stats"
    assert (await client.get(url)).status_code == 401
    assert (await client.post("/api/v1/admin/auth/login", json=admin_creds)).status_code == 200
    for days in (7, 30, 90):
        res = await client.get(url, params={"days": days})
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["operations"]["poi_readiness"]["total"] == 0
        assert data["operations"]["poi_readiness"]["ready_unpublished"] == 0
        assert data["operations"]["publication_rate_percent"] is None
        assert data["operations"]["pending_over_48h"]["registrations"] == 0
    assert (await client.get(url, params={"days": 1})).status_code == 422


async def test_readiness_and_backlog_use_real_documents(client, admin_creds):
    db = get_db()
    now = datetime.now(timezone.utc)
    old = now - timedelta(hours=65)
    recent = now - timedelta(hours=4)
    published = (await db["poi"].insert_one({"name": "POI public", "is_active": True})).inserted_id
    ready_hidden = (await db["poi"].insert_one({"name": "POI ready", "is_active": False})).inserted_id
    blocked = (await db["poi"].insert_one({"name": "POI not ready", "is_active": False, "owner_id": "owner-a"})).inserted_id
    legacy_public = (await db["poi"].insert_one({"name": "Legacy bad", "is_active": True})).inserted_id
    await db["poi_localizations"].insert_many([
        {"poi_id": published, "lang": "en", "title": "Title", "description": "Description", "audio_status": "completed", "audio_url": "/audio/a.mp3"},
        {"poi_id": ready_hidden, "lang": "en", "title": "  Title ", "description": " Description ", "audio_status": "completed", "audio_url": "/audio/b.mp3"},
        {"poi_id": blocked, "lang": "en", "title": "Name", "description": " ", "audio_status": "pending", "audio_url": ""},
        {"poi_id": legacy_public, "lang": "en", "title": "", "description": "", "audio_status": "pending", "audio_url": None},
    ])
    await db["poi_owner_registrations"].insert_many([
        {"status": "pending", "created_at": old},
        {"status": "pending", "created_at": recent},
        {"status": "approved", "created_at": old},
    ])
    await db["poi_submissions"].insert_many([
        {"status": "pending", "created_at": old},
        {"status": "rejected", "created_at": old},
    ])
    await db["audio_tasks"].insert_one({"status": "failed"})
    assert (await client.post("/api/v1/admin/auth/login", json=admin_creds)).status_code == 200
    results = []
    for days in (7, 30):
        response = await client.get("/api/v1/admin/dashboard/stats", params={"days": days})
        assert response.status_code == 200, response.text
        results.append(response.json())
    readiness = results[0]["operations"]["poi_readiness"]
    assert readiness == {
        "total": 4, "published": 2, "ready": 2,
        "ready_unpublished": 1, "blocked_unpublished": 1,
        "published_not_ready": 1, "missing_english_content": 2,
        "missing_english_audio": 2, "linked_to_owner": 1,
    }
    assert results[0]["operations"]["publication_rate_percent"] == 50.0
    assert results[0]["operations"]["readiness_rate_percent"] == 50.0
    assert results[0]["operations"]["pending_over_48h"] == {
        "threshold_hours": 48, "registrations": 1, "submissions": 1,
    }
    assert results[0]["summary"]["audio"]["failed"] == 1
    assert results[0]["summary"]["registrations"]["pending"] == 2
    assert results[0]["operations"] == results[1]["operations"]  # current snapshot ignores days
