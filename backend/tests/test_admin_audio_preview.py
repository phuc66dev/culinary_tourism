"""Admin audio preview: existing MP3s, protected download, missing and unsafe paths."""
from datetime import datetime, timezone

from bson import ObjectId

from app.core.database import get_db
from app.modules.admin import audio_preview
from app.modules.audio.service import cache_key

BASE = "/api/v1/admin/pois"


async def _login(client, admin_creds):
    response = await client.post("/api/v1/admin/auth/login", json=admin_creds)
    assert response.status_code == 200, response.text


async def _insert_poi():
    result = await get_db()["poi"].insert_one({"name": "Ốc Oanh", "is_active": False})
    return result.inserted_id


async def test_audio_files_requires_permission_and_lists_all_languages(client, admin_creds, tmp_path, monkeypatch):
    monkeypatch.setattr(audio_preview, "AUDIO_DIR", tmp_path)
    poi_id = await _insert_poi()
    url = f"/static/audio/{cache_key('Xin chào Quận 4', 'vi')}.mp3"
    (tmp_path / url.rsplit("/", 1)[-1]).write_bytes(b"ID3fake mp3 content")
    await get_db()["poi_localizations"].insert_one({
        "poi_id": poi_id, "lang": "vi", "audio_status": "completed", "audio_url": url,
        "updated_at": datetime.now(timezone.utc),
    })

    path = f"{BASE}/{poi_id}/audios"
    assert (await client.get(path)).status_code == 401
    assert (await client.get(f"{BASE}/{poi_id}/audios/vi/download")).status_code == 401
    assert (await client.get(f"{BASE}/{poi_id}/audios/vi/play")).status_code == 401
    await _login(client, admin_creds)

    response = await client.get(path)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["poi_name"] == "Ốc Oanh"
    assert len(body["items"]) == 5
    vi = body["items"][0]
    assert vi["lang"] == "vi" and vi["ready"] is True
    assert vi["audio_url"] == url
    assert vi["size_bytes"] == len(b"ID3fake mp3 content")
    assert vi["voice"] == "vi-VN-HoaiMyNeural"
    assert all(not entry["ready"] for entry in body["items"][1:])
    assert response.headers["cache-control"] == "no-store"

    streamed = await client.get(f"{BASE}/{poi_id}/audios/vi/play")
    assert streamed.status_code == 200, streamed.text
    assert streamed.content == b"ID3fake mp3 content"
    assert streamed.headers["content-type"].startswith("audio/mpeg")
    assert "inline" in streamed.headers["content-disposition"]
    assert streamed.headers["cache-control"] == "no-store"

    downloaded = await client.get(f"{BASE}/{poi_id}/audios/vi/download")
    assert downloaded.status_code == 200, downloaded.text
    assert downloaded.content == b"ID3fake mp3 content"
    assert downloaded.headers["content-type"].startswith("audio/mpeg")
    assert "attachment" in downloaded.headers["content-disposition"]
    assert f"quan4_{poi_id}_vi.mp3" in downloaded.headers["content-disposition"]


async def test_missing_and_stale_audio_do_not_appear_playable(client, admin_creds, tmp_path, monkeypatch):
    monkeypatch.setattr(audio_preview, "AUDIO_DIR", tmp_path)
    poi_id = await _insert_poi()
    name = f"{cache_key('nội dung EN', 'en')}.mp3"
    await get_db()["poi_localizations"].insert_one({
        "poi_id": poi_id, "lang": "en", "audio_status": "completed", "audio_url": f"/static/audio/{name}",
    })
    await _login(client, admin_creds)
    result = (await client.get(f"{BASE}/{poi_id}/audios")).json()
    assert next(r for r in result["items"] if r["lang"] == "en")["ready"] is False
    assert (await client.get(f"{BASE}/{poi_id}/audios/en/download")).status_code == 404
    assert (await client.get(f"{BASE}/{poi_id}/audios/en/play")).status_code == 404

    # Stale TTS metadata alone is insufficient even when file exists.
    (tmp_path / name).write_bytes(b"ID3example")
    await get_db()["poi_localizations"].update_one(
        {"poi_id": poi_id, "lang": "en"}, {"$set": {"audio_status": "pending"}}
    )
    result = (await client.get(f"{BASE}/{poi_id}/audios")).json()
    assert next(r for r in result["items"] if r["lang"] == "en")["ready"] is False
    assert (await client.get(f"{BASE}/{poi_id}/audios/en/download")).status_code == 404
    assert (await client.get(f"{BASE}/{poi_id}/audios/en/play")).status_code == 404


async def test_audio_path_from_database_is_never_used_for_traversal(client, admin_creds, tmp_path, monkeypatch):
    monkeypatch.setattr(audio_preview, "AUDIO_DIR", tmp_path)
    poi_id = await _insert_poi()
    await _login(client, admin_creds)
    loc = get_db()["poi_localizations"]
    await loc.insert_one({"poi_id": poi_id, "lang": "vi", "audio_status": "completed"})
    evil_urls = [
        "/static/audio/../../secret.mp3",
        "/static/audio/%2e%2e%2fsecret.mp3",
        "/static/audio/folder/abc.mp3",
        "file:///etc/passwd",
        "https://example.com/track.mp3",
        "/static/audio/ABCDEF.mp3",
    ]
    for url in evil_urls:
        await loc.update_one({"poi_id": poi_id, "lang": "vi"}, {"$set": {"audio_url": url}})
        result = (await client.get(f"{BASE}/{poi_id}/audios")).json()
        assert result["items"][0]["ready"] is False, url
        assert (await client.get(f"{BASE}/{poi_id}/audios/vi/download")).status_code == 404, url


async def test_audio_endpoints_validate_poi_and_lang(client, admin_creds):
    await _login(client, admin_creds)
    invalid = await client.get(f"{BASE}/garbage/audios")
    assert invalid.status_code == 400
    missing = ObjectId()
    assert (await client.get(f"{BASE}/{missing}/audios")).status_code == 404
    poi_id = await _insert_poi()
    assert (await client.get(f"{BASE}/{poi_id}/audios/xx/download")).status_code == 422
    assert (await client.get(f"{BASE}/{poi_id}/audios/xx/play")).status_code == 422
    assert (await client.get(f"{BASE}/{poi_id}/audios/vi/download")).status_code == 404
