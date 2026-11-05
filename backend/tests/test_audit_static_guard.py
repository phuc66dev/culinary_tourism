"""Tasks 3.10–3.11: audit persistence/filtering and static traversal defense.

Run: cd backend && pytest -q tests/test_audit_static_guard.py
The project conftest requires mongomock-motor; no running MongoDB is needed.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.core import database
from app.core.path_security import resolve_safe_path
from app.core.static_guard import GuardedStaticFiles
from app.modules.admin.audit import _redact, fingerprint_login


@pytest.mark.parametrize("candidate", [
    "../../etc/passwd", "maps/../secret.txt", "audio/./clip.mp3", "../static_evil/x",
    "/etc/passwd", "\\\\server\\share", "C:\\Windows\\win.ini", "audio\\..\\secret",
    "maps/%2e%2e/secret.txt", "maps/%252e%252e/secret.txt", "maps/a%2fb.txt",
    "maps/.env", "maps//foo.pmtiles", "maps/\x00foo.pmtiles", "maps/\nfoo.pmtiles",
])
def test_path_guard_denies_traversal_and_ambiguous_paths(tmp_path: Path, candidate: str):
    with pytest.raises(HTTPException) as exc:
        resolve_safe_path(tmp_path, candidate)
    assert exc.value.status_code == 403


def test_path_guard_accepts_normal_files_and_denies_symlinks(tmp_path: Path):
    base = tmp_path / "static"
    base.mkdir()
    (base / "maps").mkdir()
    (base / "maps" / "quan4.pmtiles").write_bytes(b"demo")
    assert resolve_safe_path(base, "maps/quan4.pmtiles") == (base / "maps" / "quan4.pmtiles").resolve()
    outside = tmp_path / "outside.txt"
    outside.write_text("classified")
    try:
        (base / "maps" / "shortcut.pmtiles").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Creating symlinks requires special privileges on this OS")
    with pytest.raises(HTTPException) as exc:
        resolve_safe_path(base, "maps/shortcut.pmtiles")
    assert exc.value.status_code == 403
    (base / "audio").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(HTTPException):
        resolve_safe_path(base, "audio/outside.txt")


@pytest.mark.asyncio
async def test_static_mount_enforces_guard_and_keeps_assets_accessible(tmp_path: Path):
    (tmp_path / "maps").mkdir()
    (tmp_path / "audio").mkdir()
    (tmp_path / "maps" / "quan4.pmtiles").write_bytes(b"PMTiles data")
    (tmp_path / "audio" / "voice.mp3").write_bytes(b"mp3 data")
    app = FastAPI()
    app.mount("/static", GuardedStaticFiles(directory=str(tmp_path)), name="static")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        good = await client.get("/static/maps/quan4.pmtiles")
        assert good.status_code == 200 and good.content == b"PMTiles data"
        assert (await client.get("/static/audio/voice.mp3")).content == b"mp3 data"
        assert (await client.get("/static/audio/secrets.txt")).status_code == 403
        assert (await client.get("/static/secrets.txt")).status_code == 403
        assert (await client.get("/static/maps/%252e%252e/secrets.txt")).status_code == 403
        assert (await client.get("/static/maps/.env")).status_code == 403
        assert (await client.get("/static/maps/missing.pmtiles")).status_code == 404


def test_audit_details_redaction_and_fingerprint():
    result = _redact({
        "poi_name": "Ốc Oanh", "dataset_version": 4,
        "password": "123456", "cccd_number": "123456789123", "jwt_token": "fake.jwt",
        "sub": {"cookie": "secret", "ok": True},
    })
    assert result["poi_name"] == "Ốc Oanh"
    assert result["dataset_version"] == 4
    assert result["password"] == "[redacted]"
    assert result["cccd_number"] == "[redacted]"
    assert result["jwt_token"] == "[redacted]"
    assert result["sub"]["cookie"] == "[redacted]"
    assert fingerprint_login("ADMIN@example.com") == fingerprint_login(" admin@EXAMPLE.COM ")
    assert "admin" not in fingerprint_login("admin@example.com")


@pytest.mark.asyncio
async def test_audit_auth_crud_deletion_snapshot_and_filters(client, admin_creds):
    endpoint = "/api/v1/admin/audit-logs"
    assert (await client.get(endpoint)).status_code == 401
    assert (await client.post(endpoint, json={"action": "evil"})).status_code in (401, 405)
    assert (await client.post("/api/v1/admin/auth/login", json={"email": "nonexistent@example.com", "password": "wrong"})).status_code == 401
    # Invalid email format is rejected by request validation before authentication.
    assert (await client.post("/api/v1/admin/auth/login", json={"email": "no@such.invalid", "password": "wrong"})).status_code == 422
    assert (await client.post("/api/v1/admin/auth/login", json=admin_creds)).status_code == 200
    p = await client.post("/api/v1/admin/pois", json={
        "name": "Ốc Oanh", "address": "7 Vĩnh Khánh", "ward": "Phường 8",
        "category": "street_food", "location": {"type": "Point", "coordinates": [106.702, 10.758]},
        "original_description": "Quán ốc ngon", "images": [],
    })
    assert p.status_code == 201, p.text
    pid = p.json()["id"]
    deleted = await client.delete(f"/api/v1/admin/pois/{pid}")
    assert deleted.status_code == 200, deleted.text
    response = await client.get(endpoint, params={"action": "poi.delete", "q": "Ốc Oanh", "limit": 10})
    assert response.status_code == 200, response.text
    logs = response.json()
    assert logs["total"] == 1
    item = logs["items"][0]
    assert item["action"] == "poi.delete"
    assert item["resource"] == f"poi:{pid}"
    assert item["details"]["poi_name"] == "Ốc Oanh"
    assert item["details"]["deleted_poi"] == 1
    assert item["user_id"] and item["actor_email"] == admin_creds["email"]
    assert item["created_at"] and item["ip"]
    by_actor = await client.get(endpoint, params={"user_id": item["user_id"], "action": "poi.create"})
    assert by_actor.json()["total"] == 1
    assert (await client.get(endpoint, params={"action": "poi.delete", "limit": 1, "skip": 1})).json()["items"] == []
    future = datetime.now(timezone.utc) + timedelta(days=1)
    assert (await client.get(endpoint, params={"from_time": future.isoformat()})).json()["total"] == 0
    bad_time = await client.get(endpoint, params={"from_time": future.isoformat(), "to_time": datetime.now(timezone.utc).isoformat()})
    assert bad_time.status_code == 422
    # Authentication failure is logged by an opaque fingerprint, not a raw email.
    failures = (await client.get(endpoint, params={"action": "auth.login_failed"})).json()
    assert failures["total"] == 1
    assert "email" not in str(failures["items"][0]["details"]).lower()
