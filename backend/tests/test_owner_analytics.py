from datetime import datetime, timedelta, timezone
from uuid import uuid4

from bson import ObjectId

from app.core.database import get_db
from app.core.security import hash_password


async def test_owner_analytics_requires_consent_deduplicates_and_scopes_stats(client):
    db = get_db()
    owner = (await db["users"].insert_one({
        "email": "analytics-owner@example.com",
        "password_hash": hash_password("AnalyticsTest123!"),
        "role": "poi_owner",
        "is_poi_owner_verified": True,
    })).inserted_id
    poi = (await db["poi"].insert_one({"owner_id": owner, "is_active": True})).inserted_id
    other = (await db["poi"].insert_one({"owner_id": ObjectId(), "is_active": True})).inserted_id
    inactive = (await db["poi"].insert_one({"owner_id": owner, "is_active": False})).inserted_id
    playback = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    def event(kind, poi_id=poi, **fields):
        return {"event_id": str(uuid4()), "poi_id": str(poi_id), "kind": kind, "occurred_at": now, **fields}

    events = [
        event("poi_viewed"), event("search_poi_selected"),
        event("audio_started", playback_id=playback, language="vi"),
        event("audio_completed", playback_id=playback, language="vi", duration_seconds=32),
        event("audio_ended", playback_id=playback, language="vi", duration_seconds=32),
        event("poi_viewed", other),
        event("poi_viewed", inactive),
    ]
    older = (datetime.fromisoformat(now) - timedelta(days=8)).isoformat()
    partial_playback = str(uuid4())
    for kind, fields in [
        ("audio_started", {}),
        ("audio_ended", {"duration_seconds": 15.5}),
    ]:
        events.append(event(kind, playback_id=partial_playback, language="en") | {
            "occurred_at": older, **fields,
        })
    path = "/api/v1/analytics/collect"
    rejected = await client.post(path, json={"consent_status": "denied", "events": events})
    assert rejected.status_code == 422
    assert await db["analytics_poi_events"].count_documents({}) == 0
    for expected in (7, 0):
        result = await client.post(path, json={"consent_status": "granted", "events": events})
        assert result.status_code == 200, result.text
        assert result.json()["recorded"] == expected

    assert (await client.post("/api/v1/admin/auth/login", json={
        "email": "analytics-owner@example.com", "password": "AnalyticsTest123!",
    })).status_code == 200
    result = await client.get("/api/v1/owner/analytics", params={"poi_id": str(poi), "days": 7})
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["totals"] == {
        "views": 1, "search_selections": 1, "audio_starts": 1,
        "audio_completions": 1, "listen_seconds": 32,
    }
    assert len(data["daily"]) == 7 and data["daily"][-1]["views"] == 1
    assert data["languages"] == [{"language": "vi", "audio_starts": 1}]
    month = (await client.get("/api/v1/owner/analytics", params={"poi_id": str(poi), "days": 30})).json()
    assert month["totals"]["audio_starts"] == 2
    assert month["totals"]["audio_completions"] == 1
    assert month["totals"]["listen_seconds"] == 47.5
    assert month["languages"] == [
        {"language": "en", "audio_starts": 1}, {"language": "vi", "audio_starts": 1},
    ]
    empty = (await client.get("/api/v1/owner/analytics", params={"poi_id": str(inactive), "days": 7})).json()
    assert not any(empty["totals"].values())
    assert (await client.get("/api/v1/owner/analytics", params={"poi_id": str(other)})).status_code == 404
