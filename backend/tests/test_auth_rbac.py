import pytest
from bson import ObjectId

from app.core import database
from app.core.rbac import ALL_PERMISSIONS, DEFAULT_ROLES, require_permission
from app.core.security import hash_password, resolve_safe_path

LOGIN = "/api/v1/admin/auth/login"
ME = "/api/v1/admin/auth/me"


async def _make_user(email, role, password="Passw0rd!", active=True):
    res = await database.get_db()["users"].insert_one(
        {"email": email, "password_hash": hash_password(password), "role": role, "is_active": active}
    )
    return str(res.inserted_id)


def test_permission_catalog():
    assert len(ALL_PERMISSIONS) == 32
    assert len(set(ALL_PERMISSIONS)) == 32
    assert set(DEFAULT_ROLES) == {"super_admin", "admin", "poi_owner", "user"}


def test_require_permission_rejects_typo():
    with pytest.raises(ValueError):
        require_permission("poi:aprove")


async def test_ensure_roles_idempotent_and_keeps_custom_permissions(client):
    from app.modules.admin.service import admin_service

    db = database.get_db()
    await db["roles"].update_one({"name": "admin"}, {"$set": {"permissions": ["poi:read"]}})
    await admin_service.ensure_roles()
    assert await db["roles"].count_documents({}) == 4
    assert (await db["roles"].find_one({"name": "admin"}))["permissions"] == ["poi:read"]
    assert len((await db["roles"].find_one({"name": "super_admin"}))["permissions"]) == 32


async def test_login_sets_httponly_cookies_and_me(client, admin_creds):
    r = await client.post(LOGIN, json=admin_creds)
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["role"] == "super_admin" and len(body["user"]["permissions"]) == 32
    set_cookie = " ".join(r.headers.get_list("set-cookie")).lower()
    assert "access_token=" in set_cookie and "refresh_token=" in set_cookie
    assert "httponly" in set_cookie and "samesite=lax" in set_cookie
    assert "path=/api/v1/admin/auth" in set_cookie  # refresh cookie bị giới hạn path
    me = await client.get(ME)  # cookie jar tự gửi lại
    assert me.status_code == 200 and me.json()["email"] == admin_creds["email"]


async def test_login_wrong_password_and_unknown_email(client, admin_creds):
    bad = await client.post(LOGIN, json={**admin_creds, "password": "nope"})
    unknown = await client.post(LOGIN, json={"email": "x@y.vn", "password": "nope"})
    assert bad.status_code == unknown.status_code == 401
    assert bad.json() == unknown.json()  # không lộ email có tồn tại hay không
    assert await database.get_db()["audit_logs"].count_documents({"action": "auth.login_failed"}) == 2


async def test_bearer_fallback_and_cookie_priority(client, admin_creds):
    token = (await client.post(LOGIN, json=admin_creds)).json()["access_token"]
    client.cookies.clear()
    assert (await client.get(ME)).status_code == 401
    ok = await client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200


async def test_refresh_flow_and_token_type_confusion(client, admin_creds):
    body = (await client.post(LOGIN, json=admin_creds)).json()
    # refresh token KHÔNG được dùng như access token (và ngược lại)
    client.cookies.clear()
    bad = await client.get(ME, headers={"Authorization": f"Bearer {body['refresh_token']}"})
    assert bad.status_code == 401
    r = await client.post("/api/v1/admin/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert r.status_code == 200 and r.json()["user"]["email"] == admin_creds["email"]
    client.cookies.clear()  # cookie luôn được ưu tiên hơn body
    r2 = await client.post("/api/v1/admin/auth/refresh", json={"refresh_token": body["access_token"]})
    assert r2.status_code == 401  # access token không dùng để refresh được
    assert (await client.post("/api/v1/admin/auth/refresh")).status_code == 401  # thiếu token


async def test_logout_clears_cookies(client, admin_creds):
    await client.post(LOGIN, json=admin_creds)
    r = await client.post("/api/v1/admin/auth/logout")
    assert r.status_code == 200
    client.cookies.clear()
    assert (await client.get(ME)).status_code == 401


async def test_rbac_403_vs_200_and_dynamic_change(client, admin_creds):
    await _make_user("owner@t.vn", "poi_owner")
    await client.post(LOGIN, json={"email": "owner@t.vn", "password": "Passw0rd!"})
    assert (await client.get("/api/v1/admin/users")).status_code == 403  # thiếu user:read
    # Dynamic RBAC: cấp quyền trong DB → có hiệu lực ngay, không cần đăng nhập lại
    await database.get_db()["roles"].update_one({"name": "poi_owner"}, {"$push": {"permissions": "user:read"}})
    assert (await client.get("/api/v1/admin/users")).status_code == 200


async def test_unauthenticated_is_401_and_deactivated_user_blocked(client, admin_creds):
    assert (await client.get("/api/v1/admin/roles")).status_code == 401
    uid = await _make_user("a@t.vn", "admin")
    await client.post(LOGIN, json={"email": "a@t.vn", "password": "Passw0rd!"})
    assert (await client.get(ME)).status_code == 200
    await database.get_db()["users"].update_one({"_id": ObjectId(uid)}, {"$set": {"is_active": False}})
    assert (await client.get(ME)).status_code == 401
    assert (await client.post(LOGIN, json={"email": "a@t.vn", "password": "Passw0rd!"})).status_code == 401


async def test_admin_cannot_manage_roles_but_super_admin_can(client):
    await _make_user("adm@t.vn", "admin")
    await client.post(LOGIN, json={"email": "adm@t.vn", "password": "Passw0rd!"})
    assert (await client.get("/api/v1/admin/roles")).status_code == 403  # admin không có role:*


def test_resolve_safe_path(tmp_path):
    base = tmp_path / "static"
    base.mkdir()
    (tmp_path / "static_evil").mkdir()
    assert resolve_safe_path(base, "audio/a.mp3") == (base / "audio/a.mp3").resolve()
    from fastapi import HTTPException

    for bad in ("../../etc/passwd", "../static_evil/x", "/../../etc/passwd", "audio/../../x"):
        with pytest.raises(HTTPException):
            resolve_safe_path(base, bad)
