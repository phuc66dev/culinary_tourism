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
    r = await client.post(f"{BASE}/{rid}/review", json={"action": "approve", "admin_note": "  Hồ sơ hợp lệ  "})
    assert r.status_code == 200 and r.json() == {"id": rid, "status": "approved"}
    db = database.get_db()
    assert (await db["users"].find_one({"_id": uid}))["is_poi_owner_verified"] is True
    reg = await db["poi_owner_registrations"].find_one({"_id": ObjectId(rid)})
    assert reg["status"] == "approved" and reg["admin_note"] == "Hồ sơ hợp lệ" and reg["reviewed_by"] and reg["reviewed_at"]
    note = await db["owner_notifications"].find_one({"user_id": uid})
    assert note["is_read"] is False and "duyệt" in note["message"]
    assert await db["audit_logs"].count_documents({"action": "owner.registration_approve"}) == 1


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
    assert (await client.post(f"{BASE}/{rid}/review", json={"action": "approve"})).status_code == 200
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
