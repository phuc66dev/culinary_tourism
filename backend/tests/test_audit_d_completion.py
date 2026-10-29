"""D. Audit + Static security regression checks.

cd backend && python -m pytest -q tests/test_audit_d_completion.py
Required dev packages: requirements-dev.txt
"""
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.path_security import resolve_safe_path
from app.core.static_guard import GuardedStaticFiles
from app.modules.audio.task_manager import audio_task_manager


@pytest.mark.parametrize("path", [
    "maps/CON.pmtiles", "audio/NUL.mp3", "images/COM1.jpg", "images/lpt9.PNG",
    "images/trailing .jpg ", "audio/NUL .mp3", "images/CONIN$.png", "maps/folder./file.pmtiles", "maps/folder /pack.pmtiles",
    "maps/valid%zz.pmtiles", "maps/a%252fetc.pmtiles", "maps/../files.pbf",
    "images/.secret.jpg", "maps\\..\\secrets.txt", "C:/Windows/win.ini",
])
def test_windows_special_paths_are_forbidden(tmp_path: Path, path: str):
    with pytest.raises(HTTPException) as exc:
        resolve_safe_path(tmp_path, path)
    assert exc.value.status_code == 403


def test_legal_windows_names_are_not_blocked(tmp_path: Path):
    for name in ("maps/quan4.pmtiles", "audio/filename.mp3", "images/oc-oanh.jpg"):
        assert resolve_safe_path(tmp_path, name).is_relative_to(tmp_path.resolve())


@pytest.mark.asyncio
async def test_mount_prevents_reserved_devices_and_exposes_allowed_assets(tmp_path: Path):
    (tmp_path / "audio").mkdir()
    (tmp_path / "images").mkdir()
    (tmp_path / "audio" / "test.mp3").write_bytes(b"voice")
    (tmp_path / "images" / "photo.jpg").write_bytes(b"photo")
    app = FastAPI()
    app.mount("/static", GuardedStaticFiles(directory=tmp_path), name="static")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        audio = await http.get("/static/audio/test.mp3")
        assert audio.content == b"voice"
        assert audio.headers["x-content-type-options"] == "nosniff"
        assert "sandbox" in audio.headers["content-security-policy"]
        assert (await http.get("/static/images/photo.jpg")).status_code == 200
        for path in ("/static/audio/CON.mp3", "/static/images/NUL.jpg", "/static/audio/a%252fsecret.mp3"):
            response = await http.get(path)
            assert response.status_code == 403, (path, response.text)


@pytest.mark.asyncio
async def test_admin_audio_mutations_have_actor_audit_and_resource_filter(client, admin_creds, monkeypatch):
    # Do not run TTS workers; this test concerns durable queue/control + audit only.
    monkeypatch.setattr(audio_task_manager, "_start", lambda _task_id: None)
    assert (await client.post("/api/v1/admin/auth/login", json=admin_creds)).status_code == 200
    poi = await client.post("/api/v1/admin/pois", json={
        "name": "Ốc Oanh", "address": "7 Vĩnh Khánh", "ward": "Phường 8",
        "category": "street_food", "location": {"type": "Point", "coordinates": [106.702, 10.758]},
        "original_description": "Quán ốc ngon", "images": [],
    })
    assert poi.status_code == 201, poi.text
    poi_id = poi.json()["id"]
    created = await client.post("/api/v1/admin/audio-tasks", json={"poi_id": poi_id, "languages": ["vi"]})
    assert created.status_code == 202, created.text
    task_id = created.json()["id"]
    paused = await client.post(f"/api/v1/admin/audio-tasks/{task_id}/pause")
    assert paused.status_code == 200, paused.text
    cancelled = await client.post(f"/api/v1/admin/audio-tasks/{task_id}/cancel")
    assert cancelled.status_code == 200, cancelled.text

    audit = await client.get("/api/v1/admin/audit-logs", params={"resource": f"audio_task:{task_id}"})
    assert audit.status_code == 200, audit.text
    items = audit.json()["items"]
    assert {item["action"] for item in items} == {"audio.task_enqueue", "audio.task_pause", "audio.task_cancel"}
    assert all(item["user_id"] and item["created_at"] for item in items)
    changed = next(item for item in items if item["action"] == "audio.task_pause")
    assert changed["details"]["from_status"] == "queued"
    assert changed["details"]["to_status"] == "paused"


@pytest.mark.asyncio
async def test_admin_audit_filter_resource_does_not_expose_other_objects(client, admin_creds):
    assert (await client.post("/api/v1/admin/auth/login", json=admin_creds)).status_code == 200
    res = await client.get("/api/v1/admin/audit-logs", params={"resource": "poi:does-not-exist"})
    assert res.status_code == 200
    assert res.json()["total"] == 0


@pytest.mark.asyncio
async def test_login_refresh_logout_leave_audit_events(client, admin_creds):
    auth = "/api/v1/admin/auth"
    first = await client.post(f"{auth}/login", json=admin_creds)
    assert first.status_code == 200, first.text
    actor_id = first.json()["user"]["id"]
    refreshed = await client.post(f"{auth}/refresh", json={})
    assert refreshed.status_code == 200, refreshed.text
    logged_out = await client.post(f"{auth}/logout")
    assert logged_out.status_code == 200, logged_out.text
    assert (await client.post(f"{auth}/login", json=admin_creds)).status_code == 200
    response = await client.get("/api/v1/admin/audit-logs", params={"resource": f"user:{actor_id}"})
    assert response.status_code == 200, response.text
    actions = [log["action"] for log in response.json()["items"]]
    assert "auth.login" in actions
    assert "auth.refresh" in actions
    assert "auth.logout" in actions
