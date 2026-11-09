"""Task 3.5 — Duyệt đơn đăng ký chủ quán & giải mã CCCD (PII)."""
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from cryptography.fernet import Fernet

from app.core import database
from app.core.config import settings
from app.core.security import hash_password

LOGIN = "/api/v1/admin/auth/login"
BASE = "/api/v1/admin/registrations"
CCCD = "079201001234"


@pytest.fixture
def fernet(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "FERNET_KEY", key)
    return Fernet(key.encode())


async def make_registration(fernet, n=1, status="pending", cccd=CCCD, with_cipher=True):
    db = database.get_db()
    user = await db["users"].insert_one(
        {"email": f"owner{n}@t.vn", "password_hash": hash_password("Passw0rd!"), "role": "poi_owner",
         "is_active": True, "is_poi_owner_verified": False}
    )
    doc = {
        "user_id": user.inserted_id, "full_name": f"Chủ Quán {n}", "phone": f"09000000{n}",
        "poi_name": f"Quán Số {n}", "poi_address": "1 Vĩnh Khánh, Quận 4", "storefront_image_url": "/static/images/poi/x.webp",
        "status": status, "created_at": datetime.now(timezone.utc) - timedelta(hours=n),
    }
    if with_cipher:
        doc["cccd_encrypted"] = "v1:" + fernet.encrypt(cccd.encode()).decode()
    res = await db["poi_owner_registrations"].insert_one(doc)
    return str(res.inserted_id), user.inserted_id


DRAFT = {
    "ward": "Phường 10",
    "location": {"type": "Point", "coordinates": [106.703, 10.76]},
    "original_description": "Quán phục vụ các món ăn địa phương.",
}


async def make_poi(name="Quán Số 1", address="1 Vĩnh Khánh, Quận 4", **fields):
    doc = {"name": name, "address": address, "is_active": False, **fields}
    result = await database.get_db()["poi"].insert_one(doc)
    return result.inserted_id


async def admin_login(client):
    r = await client.post(LOGIN, json={"email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD})
    assert r.status_code == 200


async def test_requires_auth_and_permission(client, fernet):
    rid, _ = await make_registration(fernet)
    assert (await client.get(BASE)).status_code == 401
    await client.post(LOGIN, json={"email": "owner1@t.vn", "password": "Passw0rd!"})  # poi_owner
    assert (await client.get(BASE)).status_code == 403
    assert (await client.get(f"{BASE}/{rid}/cccd")).status_code == 403
    assert (await client.post(f"{BASE}/{rid}/review", json={"action": "approve"})).status_code == 403


async def test_list_never_leaks_cccd_and_supports_filters(client, fernet):
    await make_registration(fernet, 1)
    await make_registration(fernet, 2, status="approved")
    await make_registration(fernet, 3, with_cipher=False)
    await admin_login(client)
    body = (await client.get(BASE)).json()
    raw = (await client.get(BASE)).text
    assert CCCD not in raw and "cccd_encrypted" not in raw and "v1:" not in raw
    assert len(body["items"]) == 3 and body["counts"] == {"pending": 2, "approved": 1, "rejected": 0}
    by_name = {i["poi_name"]: i for i in body["items"]}
    assert by_name["Quán Số 1"]["cccd_available"] is True and by_name["Quán Số 3"]["cccd_available"] is False
    assert by_name["Quán Số 1"]["email"] == "owner1@t.vn"
    assert [i["poi_name"] for i in body["items"]] == ["Quán Số 1", "Quán Số 2", "Quán Số 3"]  # mới nhất trước
    pending = (await client.get(BASE, params={"status": "pending"})).json()["items"]
    assert {i["poi_name"] for i in pending} == {"Quán Số 1", "Quán Số 3"}
    assert (await client.get(BASE, params={"status": "weird"})).status_code == 422
    found = (await client.get(BASE, params={"q": "owner2@"})).json()["items"]
    assert [i["poi_name"] for i in found] == ["Quán Số 2"]


async def test_reveal_cccd_decrypts_audits_and_no_store(client, fernet):
    rid, _ = await make_registration(fernet)
    await admin_login(client)
    r = await client.get(f"{BASE}/{rid}/cccd")
    assert r.status_code == 200 and r.json() == {"cccd_number": CCCD}
    assert r.headers["cache-control"] == "no-store"
    log = await database.get_db()["audit_logs"].find_one({"action": "owner.cccd_reveal"})
    assert log["resource"] == f"registration:{rid}" and log["user_id"]
    assert CCCD not in str(log)  # audit không chứa PII


async def test_reveal_cccd_errors(client, fernet, monkeypatch):
    rid, _ = await make_registration(fernet)
    nocipher, _ = await make_registration(fernet, 2, with_cipher=False)
    await admin_login(client)
    assert (await client.get(f"{BASE}/not-an-id/cccd")).status_code == 400
    assert (await client.get(f"{BASE}/{ObjectId()}/cccd")).status_code == 404
    assert (await client.get(f"{BASE}/{nocipher}/cccd")).status_code == 404
    monkeypatch.setattr(settings, "FERNET_KEY", Fernet.generate_key().decode())  # sai khoá
    assert (await client.get(f"{BASE}/{rid}/cccd")).status_code == 422
    monkeypatch.setattr(settings, "FERNET_KEY", "")
    assert (await client.get(f"{BASE}/{rid}/cccd")).status_code == 503
    monkeypatch.setattr(settings, "FERNET_KEY", "not-a-key")
    assert (await client.get(f"{BASE}/{rid}/cccd")).status_code == 503
    assert await database.get_db()["audit_logs"].count_documents({"action": "owner.cccd_reveal"}) == 0


async def test_approve_sets_verified_flag_and_notifies(client, fernet):
    rid, uid = await make_registration(fernet)
    await admin_login(client)
    pid = await make_poi()
    r = await client.post(f"{BASE}/{rid}/review", json={
        "action": "approve", "admin_note": "  Hồ sơ hợp lệ  ", "poi_id": str(pid),
    })
    assert r.status_code == 200 and r.json() == {"id": rid, "status": "approved", "poi_id": str(pid)}
    db = database.get_db()
    assert (await db["users"].find_one({"_id": uid}))["is_poi_owner_verified"] is True
    reg = await db["poi_owner_registrations"].find_one({"_id": ObjectId(rid)})
    assert reg["status"] == "approved" and reg["admin_note"] == "Hồ sơ hợp lệ" and reg["reviewed_by"] and reg["reviewed_at"]
    assert reg["linked_poi_id"] == pid
    assert (await db["poi"].find_one({"_id": pid}))["owner_id"] == uid
    assert await db["poi"].count_documents({}) == 1
    note = await db["owner_notifications"].find_one({"user_id": uid})
    assert note["is_read"] is False and "duyệt" in note["message"]
    assert await db["audit_logs"].count_documents({"action": "owner.registration_approve"}) == 1
    response = await client.post(LOGIN, json={"email": "owner1@t.vn", "password": "Passw0rd!"})
    assert response.status_code == 200
    response = await client.get("/api/v1/owner/pois/me")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [str(pid)]


async def test_approve_pinned_registration_publishes_poi(client, fernet):
    registration = {
        "full_name": "Nguyễn Văn An",
        "phone": "0901234567",
        "email": "pinned@example.com",
        "password": "StrongPassword!123",
        "poi_name": "Quán Bánh Mì",
        "poi_address": "1 Vĩnh Khánh, Quận 4",
        "poi_location": DRAFT["location"],
        "cccd_number": CCCD,
    }
    response = await client.post("/api/v1/admin/auth/register-owner", json=registration)
    assert response.status_code == 201, response.text
    rid = response.json()["id"]
    db = database.get_db()
    assert await db["poi"].count_documents({}) == 0

    await admin_login(client)
    response = await client.post(f"{BASE}/{rid}/review", json={"action": "approve"})
    assert response.status_code == 200, response.text
    pid = response.json()["poi_id"]
    poi = await db["poi"].find_one({"_id": ObjectId(pid)})
    assert list(poi["location"]["coordinates"]) == registration["poi_location"]["coordinates"]
    assert poi["address"] == registration["poi_address"]
    assert poi["is_active"] is True
    assert (await client.post(f"{BASE}/{rid}/review", json={"action": "approve"})).status_code == 409
    client.cookies.clear()
    public = await client.get("/api/v1/mobile/pois", params={"search": registration["poi_name"]})
    assert public.status_code == 200, public.text
    assert [item["id"] for item in public.json()["data"]["items"]] == [pid]
    assert await db["poi"].count_documents({}) == 1


async def test_approve_legacy_registration_with_admin_pin(client, fernet):
    rid, _ = await make_registration(fernet)
    await admin_login(client)
    response = await client.post(f"{BASE}/{rid}/review", json={
        "action": "approve", "poi_location": DRAFT["location"],
    })
    assert response.status_code == 200, response.text
    db = database.get_db()
    reg = await db["poi_owner_registrations"].find_one({"_id": ObjectId(rid)})
    assert reg["status"] == "approved"
    assert list(reg["poi_location"]["coordinates"]) == DRAFT["location"]["coordinates"]
    poi = await db["poi"].find_one({"_id": ObjectId(response.json()["poi_id"])})
    assert poi["is_active"] is True


@pytest.mark.parametrize("already_owned", [False, True])
async def test_approve_pinned_registration_handles_existing_poi(client, fernet, already_owned):
    rid, uid = await make_registration(fernet)
    db = database.get_db()
    await db["poi_owner_registrations"].update_one(
        {"_id": ObjectId(rid)}, {"$set": {"poi_location": DRAFT["location"]}},
    )
    other_owner = ObjectId() if already_owned else None
    pid = await make_poi(owner_id=other_owner)
    await admin_login(client)

    response = await client.post(f"{BASE}/{rid}/review", json={"action": "approve"})
    poi = await db["poi"].find_one({"_id": pid})
    assert await db["poi"].count_documents({}) == 1
    if already_owned:
        assert response.status_code == 409, response.text
        assert poi["owner_id"] == other_owner and poi["is_active"] is False
        registration = await db["poi_owner_registrations"].find_one({"_id": ObjectId(rid)})
        assert registration["status"] == "pending"
    else:
        assert response.status_code == 200, response.text
        assert response.json()["poi_id"] == str(pid)
        assert poi["owner_id"] == uid and poi["is_active"] is True
        assert poi["location"] == DRAFT["location"]


async def test_reject_requires_reason_and_notifies_owner(client, fernet):
    rid, uid = await make_registration(fernet)
    await admin_login(client)
    for note in (None, "", "   "):
        assert (await client.post(f"{BASE}/{rid}/review", json={"action": "reject", "admin_note": note})).status_code == 422
    assert (await client.post(f"{BASE}/{rid}/review", json={"action": "reject", "admin_note": "x" * 501})).status_code == 422
    r = await client.post(f"{BASE}/{rid}/review", json={"action": "reject", "admin_note": "Ảnh mặt tiền bị mờ"})
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    db = database.get_db()
    assert (await db["users"].find_one({"_id": uid}))["is_poi_owner_verified"] is False
    note = await db["owner_notifications"].find_one({"user_id": uid})
    assert "Ảnh mặt tiền bị mờ" in note["message"] and note["admin_note"] == "Ảnh mặt tiền bị mờ"


async def test_double_review_and_bad_input(client, fernet):
    rid, _ = await make_registration(fernet)
    await admin_login(client)
    assert (await client.post(f"{BASE}/{rid}/review", json={"action": "maybe"})).status_code == 422
    assert (await client.post(f"{BASE}/{ObjectId()}/review", json={"action": "approve"})).status_code == 404
    assert (await client.post(f"{BASE}/{rid}/review", json={"action": "approve", "draft": DRAFT})).status_code == 200
    assert (await client.post(f"{BASE}/{rid}/review", json={"action": "reject", "admin_note": "đổi ý"})).status_code == 409
    assert await database.get_db()["owner_notifications"].count_documents({}) == 1  # lần 2 không gửi thêm thông báo


async def test_orphan_registration_is_409(client, fernet):
    rid, uid = await make_registration(fernet)
    await database.get_db()["users"].delete_one({"_id": uid})
    await admin_login(client)
    assert (await client.post(f"{BASE}/{rid}/review", json={"action": "approve"})).status_code == 409


async def test_cccd_rejects_unsupported_cipher_version(client, fernet):
    rid, _ = await make_registration(fernet)
    await database.get_db()["poi_owner_registrations"].update_one(
        {"_id": ObjectId(rid)},
        {"$set": {"cccd_encrypted": "v2:" + fernet.encrypt(CCCD.encode()).decode()}},
    )
    await admin_login(client)
    response = await client.get(f"{BASE}/{rid}/cccd")
    assert response.status_code == 422
    assert await database.get_db()["audit_logs"].count_documents({"action": "owner.cccd_reveal"}) == 0


async def test_search_by_name_or_address_and_block_other_owner(client, fernet):
    rid, uid = await make_registration(fernet)
    pid = await make_poi(owner_id=ObjectId())
    other = await make_poi(name="Quán khác")
    await admin_login(client)
    response = await client.get(f"{BASE}/{rid}/poi-candidates", params={"name": "quan so", "address": "vinh khanh"})
    assert response.status_code == 200
    assert response.json()["has_exact_match"] is True
    assert {item["id"]: item["can_link"] for item in response.json()["items"]} == {str(pid): False}
    by_address = await client.get(f"{BASE}/{rid}/poi-candidates", params={"address": "vinh khanh"})
    assert {item["id"] for item in by_address.json()["items"]} == {str(pid), str(other)}
    blocked = await client.post(f"{BASE}/{rid}/review", json={"action": "approve", "poi_id": str(pid)})
    assert blocked.status_code == 409
    assert (await database.get_db()["users"].find_one({"_id": uid}))["is_poi_owner_verified"] is False


async def test_draft_uses_registration_data_stays_hidden_and_blocks_duplicates(client, fernet):
    rid, uid = await make_registration(fernet)
    await admin_login(client)
    assert (await client.post(f"{BASE}/{rid}/review", json={"action": "approve"})).status_code == 422
    response = await client.post(f"{BASE}/{rid}/review", json={"action": "approve", "draft": DRAFT})
    assert response.status_code == 200
    pid = ObjectId(response.json()["poi_id"])
    db = database.get_db()
    poi = await db["poi"].find_one({"_id": pid})
    assert poi["name"] == "Quán Số 1" and poi["address"] == "1 Vĩnh Khánh, Quận 4"
    assert poi["is_active"] is False and poi["owner_id"] == uid
    assert poi["images"] == ["/static/images/poi/x.webp"]
    another_id, another_owner = await make_registration(fernet, n=2)
    await db["poi_owner_registrations"].update_one(
        {"_id": ObjectId(another_id)}, {"$set": {"poi_name": "quan  so 1", "poi_address": "1 vinh khanh, quan 4"}},
    )
    response = await client.post(f"{BASE}/{another_id}/review", json={"action": "approve", "draft": DRAFT})
    assert response.status_code == 409
    assert await db["poi"].count_documents({}) == 1
    assert (await db["users"].find_one({"_id": another_owner}))["is_poi_owner_verified"] is False


async def test_attach_poi_to_previously_approved_registration(client, fernet):
    rid, uid = await make_registration(fernet, status="approved")
    db = database.get_db()
    await db["poi_owner_registrations"].update_one(
        {"_id": ObjectId(rid)}, {"$set": {"admin_note": "Đã xác minh"}},
    )
    pid = await make_poi()
    await admin_login(client)
    payload = {"action": "approve", "poi_id": str(pid)}
    assert (await client.post(f"{BASE}/{rid}/review", json=payload)).status_code == 200
    assert (await client.post(f"{BASE}/{rid}/review", json=payload)).status_code == 409
    reg = await db["poi_owner_registrations"].find_one({"_id": ObjectId(rid)})
    assert reg["admin_note"] == "Đã xác minh" and reg["linked_poi_id"] == pid
    assert (await db["poi"].find_one({"_id": pid}))["owner_id"] == uid
    assert await db["owner_notifications"].count_documents({"user_id": uid}) == 1
