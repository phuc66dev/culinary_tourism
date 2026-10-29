"""Integration coverage for Tasks 3.4 and 3.6 using existing mongomock-motor fixture.

Run from backend/: pytest -q tests/test_admin_poi_review.py tests/test_registratitons.py
"""
from datetime import datetime, timezone

import pytest
from bson import ObjectId

from app.core import database
from app.core.config import settings

LOGIN = "/api/v1/admin/auth/login"
POIS = "/api/v1/admin/pois"
SUBS = "/api/v1/admin/submissions"


async def login(client, admin_creds):
    response = await client.post(LOGIN, json=admin_creds)
    assert response.status_code == 200, response.text


def sample_poi(name="Quán Kiểm Thử"):
    return {
        "name": name, "address": "10 Vĩnh Khánh, Quận 4", "ward": "Phường 8",
        "category": "street_food", "location": {"type": "Point", "coordinates": [106.704, 10.757]},
        "original_description": "Phục vụ món ngon mỗi ngày.", "images": [],
    }


@pytest.mark.asyncio
async def test_poi_crud_filters_auth_and_gate(client, admin_creds):
    assert (await client.get(POIS)).status_code == 401
    await login(client, admin_creds)
    created = await client.post(POIS, json=sample_poi())
    assert created.status_code == 201, created.text
    poi = created.json()
    pid = poi["id"]
    assert poi["is_active"] is False
    assert not poi["activation"]["ready"]
    assert len(poi["activation"]["reasons"]) == 3
    assert (await client.post(POIS, json={**sample_poi(), "is_active": True})).status_code == 409
    assert (await client.post(POIS, json={**sample_poi(), "location": {"type": "Point", "coordinates": [200, 10]}})).status_code == 422
    assert (await client.post(POIS, json={**sample_poi(), "owner_id": "hacked"})).status_code == 422
    listing = (await client.get(POIS, params={"q": "Kiểm Thử", "ward": "Phường 8", "is_active": False})).json()
    assert listing["total"] == 1 and listing["items"][0]["id"] == pid
    assert (await client.get(POIS, params={"ward": "Phường 15"})).json()["total"] == 0
    assert (await client.patch(f"{POIS}/{pid}", json={"is_active": True, "expected_revision": 1})).status_code == 409

    en = await client.put(f"{POIS}/{pid}/localizations/en", json={
        "title": "Test Restaurant", "description": "Test restaurant cuisine", "expected_revision": 1,
    })
    assert en.status_code == 200, en.text
    assert en.json()["activation"]["reasons"] == ["Chưa hoàn tất âm thanh tiếng Anh"]
    db = database.get_db()
    await db["poi_localizations"].update_one({"poi_id": ObjectId(pid), "lang": "en"}, {"$set": {
        "audio_url": "/static/audio/demo.mp3", "audio_status": "completed",
    }})
    now = await client.get(f"{POIS}/{pid}")
    assert now.json()["activation"]["ready"] is True
    assert (await client.patch(f"{POIS}/{pid}", json={"is_active": True, "expected_revision": 1})).status_code == 409
    changed = await client.patch(f"{POIS}/{pid}", json={"is_active": True, "expected_revision": 2})
    assert changed.status_code == 200 and changed.json()["is_active"] is True
    assert (await client.patch(f"{POIS}/{pid}", json={"original_description": "Nội dung khác"})).status_code == 409
    off = await client.patch(f"{POIS}/{pid}", json={"is_active": False})
    assert off.status_code == 200
    revised = await client.patch(f"{POIS}/{pid}", json={"original_description": "Nội dung khác"})
    assert revised.status_code == 200
    assert revised.json()["activation"]["ready"] is False
    en_doc = await db["poi_localizations"].find_one({"poi_id": ObjectId(pid), "lang": "en"})
    assert en_doc["description"] is None and en_doc["audio_url"] is None
    assert (await client.delete(f"{POIS}/{pid}")).status_code == 200
    assert (await client.get(f"{POIS}/{pid}")).status_code == 404
    assert (await db["poi_localizations"].count_documents({"poi_id": ObjectId(pid)})) == 0
    assert (await db["system_meta"].find_one({"_id": "dataset"}))["version"] >= 5


@pytest.mark.asyncio
async def test_submissions_diff_approval_merge_version_and_notification(client, admin_creds):
    await login(client, admin_creds)
    poi = (await client.post(POIS, json=sample_poi())).json()
    pid = ObjectId(poi["id"])
    db = database.get_db()
    owner = ObjectId()
    await db["users"].insert_one({"_id": owner, "email": "owner-submit@test.vn", "role": "poi_owner"})
    sid = (await db["poi_submissions"].insert_one({
        "poi_id": pid, "user_id": owner, "status": "pending",
        "proposed_changes": {"name": "Quán Đã Đổi Tên", "address": "100 Vĩnh Khánh, Quận 4"},
        "created_at": datetime.now(timezone.utc),
    })).inserted_id
    data = (await client.get(SUBS, params={"status": "pending"})).json()
    assert data["total"] == 1 and data["counts"]["pending"] == 1
    item = data["items"][0]
    assert item["id"] == str(sid) and item["poi_revision"] == 1
    assert {d["field"] for d in item["diff"]} == {"name", "address"}
    assert next(d for d in item["diff"] if d["field"] == "name")["current"] == "Quán Kiểm Thử"
    assert (await client.post(f"{SUBS}/{sid}/review", json={"action": "approve"})).status_code == 409
    ok = await client.post(f"{SUBS}/{sid}/review", json={"action": "approve", "expected_revision": 1})
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "approved" and ok.json()["dataset_version"] == 2
    master = await db["poi"].find_one({"_id": pid})
    assert master["name"] == "Quán Đã Đổi Tên" and master["address"] == "100 Vĩnh Khánh, Quận 4"
    assert master["revision"] == 2
    assert await db["owner_notifications"].count_documents({"user_id": owner}) == 1
    assert (await client.post(f"{SUBS}/{sid}/review", json={"action": "approve", "expected_revision": 2})).status_code == 409
    assert (await db["system_meta"].find_one({"_id": "dataset"}))["version"] == 2


@pytest.mark.asyncio
async def test_submissions_reject_invalid_fields_and_pending_delete_gate(client, admin_creds):
    await login(client, admin_creds)
    poi = (await client.post(POIS, json=sample_poi())).json()
    pid = ObjectId(poi["id"])
    db = database.get_db()
    sid = (await db["poi_submissions"].insert_one({
        "poi_id": str(pid), "user_id": ObjectId(), "status": "pending",
        "proposed_changes": {"ward": "Phường 15"}, "created_at": datetime.now(timezone.utc),
    })).inserted_id
    assert (await client.delete(f"{POIS}/{pid}")).status_code == 409
    assert (await client.post(f"{SUBS}/{sid}/review", json={"action": "reject", "admin_note": " "})).status_code == 422
    result = await client.post(f"{SUBS}/{sid}/review", json={"action": "reject", "admin_note": "Sai địa chỉ"})
    assert result.status_code == 200 and result.json()["status"] == "rejected"
    assert (await db["poi"].find_one({"_id": pid}))["ward"] == "Phường 8"
    assert (await client.delete(f"{POIS}/{pid}")).status_code == 200


@pytest.mark.asyncio
async def test_submissions_cannot_inject_internal_fields_or_merge_stale_data(client, admin_creds):
    await login(client, admin_creds)
    poi = (await client.post(POIS, json=sample_poi())).json()
    db = database.get_db()
    sid = (await db["poi_submissions"].insert_one({
        "poi_id": poi["id"], "status": "pending", "proposed_changes": {"$set": {"is_active": True}},
        "created_at": datetime.now(timezone.utc),
    })).inserted_id
    assert (await client.post(f"{SUBS}/{sid}/review", json={"action": "approve", "expected_revision": 1})).status_code == 422
    assert (await db["poi_submissions"].find_one({"_id": sid}))["status"] == "pending"
    await db["poi_submissions"].update_one({"_id": sid}, {"$set": {"proposed_changes": {"ward": "Phường 15"}}})
    await client.patch(f"{POIS}/{poi['id']}", json={"address": "Đã sửa"})
    assert (await client.post(f"{SUBS}/{sid}/review", json={"action": "approve", "expected_revision": 1})).status_code == 409
    assert (await db["poi_submissions"].find_one({"_id": sid}))["status"] == "pending"


@pytest.mark.asyncio
async def test_owner_notifications_are_private_and_show_rejection_reasons(client):
    from app.core.security import hash_password

    db = database.get_db()
    uid = ObjectId()
    other = ObjectId()
    await db["users"].insert_one({
        "_id": uid, "email": "own-notify@example.com", "password_hash": hash_password("SomePass123!"),
        "role": "poi_owner", "is_active": True, "is_poi_owner_verified": False,
    })
    await db["users"].insert_one({
        "_id": other, "email": "other-notify@example.com", "password_hash": hash_password("SomePass123!"),
        "role": "poi_owner", "is_active": True,
    })
    notification = await db["owner_notifications"].insert_one({
        "user_id": uid, "type": "registration_review", "title": "Kết quả duyệt hồ sơ",
        "message": "Hồ sơ bị từ chối", "admin_note": "CCCD chưa rõ nét",
        "is_read": False, "created_at": datetime.now(timezone.utc),
    })
    assert (await client.get("/api/v1/owner/notifications")).status_code == 401
    assert (await client.post(LOGIN, json={"email": "own-notify@example.com", "password": "SomePass123!"})).status_code == 200
    inbox = (await client.get("/api/v1/owner/notifications")).json()
    assert inbox["total"] == 1 and inbox["unread_count"] == 1
    assert inbox["items"][0]["admin_note"] == "CCCD chưa rõ nét"
    detail = await client.get(f"/api/v1/owner/notifications/{notification.inserted_id}")
    assert detail.status_code == 200 and detail.json()["is_read"] is True
    assert (await client.get("/api/v1/owner/notifications")).json()["unread_count"] == 0
    assert (await client.post(LOGIN, json={"email": "other-notify@example.com", "password": "SomePass123!"})).status_code == 200
    assert (await client.get(f"/api/v1/owner/notifications/{notification.inserted_id}")).status_code == 404
    assert (await client.get("/api/v1/owner/notifications")).json()["total"] == 0


@pytest.mark.asyncio
async def test_registration_email_search_runs_before_pagination(client, admin_creds):
    await login(client, admin_creds)
    db = database.get_db()
    stamp = datetime.now(timezone.utc)
    for i in range(30):
        uid = (await db["users"].insert_one({
            "email": f"registration{i:02d}@sample.vn", "role": "poi_owner", "is_active": True,
        })).inserted_id
        await db["poi_owner_registrations"].insert_one({
            "user_id": uid, "full_name": f"Chủ quán {i}", "poi_name": f"Quán {i}",
            "status": "pending", "created_at": stamp,
        })
    result = await client.get('/api/v1/admin/registrations', params={
        "q": "registration29@sample.vn", "limit": 5, "skip": 0,
    })
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "registration29@sample.vn"
    page2 = (await client.get('/api/v1/admin/registrations', params={"limit": 5, "skip": 5})).json()
    assert page2["total"] == 30 and len(page2["items"]) == 5


@pytest.mark.asyncio
async def test_submission_name_search_paginates_before_serialization(client, admin_creds):
    """Regression: Mongo query must filter POI name before skip/limit."""
    await login(client, admin_creds)
    db = database.get_db()
    match = (await client.post(POIS, json=sample_poi("Quán Bún Đậu"))).json()
    another = (await client.post(POIS, json=sample_poi("Quán Phở"))).json()
    stamp = datetime.now(timezone.utc)
    await db["poi_submissions"].insert_one({
        "poi_id": ObjectId(match["id"]), "status": "pending",
        "proposed_changes": {"ward": "Phường 2"}, "created_at": stamp,
    })
    await db["poi_submissions"].insert_one({
        "poi_id": another["id"], "status": "pending",
        "proposed_changes": {"ward": "Phường 7"}, "created_at": stamp,
    })
    response = await client.get(SUBS, params={"q": "Bún Đậu", "limit": 1})
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["poi_name"] == "Quán Bún Đậu"
    response = await client.get(SUBS, params={"q": another["id"], "limit": 1})
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["poi_id"] == another["id"]
    assert (await client.get(SUBS, params={"q": "Bún Đậu", "skip": 1, "limit": 1})).json()["items"] == []
