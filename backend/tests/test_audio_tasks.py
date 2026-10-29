"""Task 3.7 / 3.8 / 3.9 — TTSService, AudioTaskManager (Semaphore, pause/resume/cancel, recovery) & SSE."""
import asyncio
import hashlib
import json
import logging

import pytest
from bson import ObjectId

from app.core import database
from app.core.security import hash_password
from app.modules.audio import service as tts_module
from app.modules.audio.service import DEFAULT_NEURAL_VOICES, SynthResult, TTSService, cache_key, split_text
from app.modules.audio.sse import audio_tasks_event_stream
from app.modules.audio.task_manager import AudioTaskManager, audio_task_manager
from app.modules.audio.task_store import audio_task_store
from app.modules.audio.source_version import source_fingerprint

LOGIN = "/api/v1/admin/auth/login"
TASKS = "/api/v1/admin/audio-tasks"
ALL_LANGS = list(DEFAULT_NEURAL_VOICES)


# ---------------------------------------------------------------- helpers
class FakeTTS:
    """Thay translate + synthesize: không cần mạng, đếm số lần gọi và độ song song."""

    def __init__(self, delay: float = 0.0):
        self.delay = delay
        self.gate: asyncio.Event | None = None
        self.synth_calls: list[str] = []
        self.active = 0
        self.max_active = 0

    async def translate(self, text, lang):
        return text if lang == "vi" else f"[{lang}] {text}"

    async def synthesize(self, text, lang):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            self.synth_calls.append(lang)
            if self.gate is not None:
                await self.gate.wait()
            await asyncio.sleep(self.delay)
            return SynthResult(f"/static/audio/{cache_key(text, lang)}.mp3", False)
        finally:
            self.active -= 1


@pytest.fixture
def fake_tts(monkeypatch):
    fake = FakeTTS()
    monkeypatch.setattr("app.modules.audio.task_manager.tts_service", fake)
    return fake


@pytest.fixture
async def manager(client):
    m = AudioTaskManager()
    yield m
    await m.shutdown()


@pytest.fixture(autouse=True)
async def _reset_singleton():
    yield
    await audio_task_manager.shutdown()


async def make_poi(name="Ốc Oanh", desc="Quán ốc nổi tiếng Vĩnh Khánh."):
    db = database.get_db()
    res = await db["poi"].insert_one({"name": name, "original_description": desc, "is_active": False})
    await db["poi_localizations"].insert_one(
        {"poi_id": res.inserted_id, "lang": "vi", "title": name, "description": desc}
    )
    return str(res.inserted_id)


async def wait_status(task_id, wanted, timeout=3.0):
    wanted = (wanted,) if isinstance(wanted, str) else wanted
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        t = await audio_task_store.get(task_id)
        if t["status"] in wanted:
            return t
        await asyncio.sleep(0.01)
    raise AssertionError(f"Task {task_id} không đạt {wanted}, hiện: {(await audio_task_store.get(task_id))['status']}")


async def admin_login(client):
    from app.core.config import settings

    r = await client.post(LOGIN, json={"email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD})
    assert r.status_code == 200


# ---------------------------------------------------------------- Task 3.7: TTSService
def test_five_standard_voices():
    assert DEFAULT_NEURAL_VOICES == {
        "vi": "vi-VN-HoaiMyNeural", "en": "en-US-JennyNeural", "zh": "zh-CN-XiaoxiaoNeural",
        "ja": "ja-JP-NanamiNeural", "ko": "ko-KR-SunHiNeural",
    }


def test_cache_key_is_md5_of_text_plus_lang():
    assert cache_key("xin chào", "vi") == hashlib.md5("xin chàovi".encode()).hexdigest()
    assert cache_key("hi", "en") != cache_key("hi", "ja")


def test_split_text_respects_limit_and_loses_nothing():
    text = " ".join(f"Câu số {i} rất là dài dòng." for i in range(400))
    chunks = split_text(text, 500)
    assert all(len(c) <= 500 for c in chunks) and len(chunks) > 1
    assert " ".join(chunks).split() == text.split()
    assert split_text("x" * 1200, 500) == ["x" * 500, "x" * 500, "x" * 200]


async def test_tts_cache_hit_skips_edge_tts(tmp_path, monkeypatch):
    monkeypatch.setattr(tts_module, "AUDIO_DIR", tmp_path)
    calls = []

    class FakeCommunicate:
        def __init__(self, text, voice):
            calls.append((text, voice))

        async def save(self, path):
            with open(path, "wb") as f:
                f.write(b"ID3fake-mp3")

    monkeypatch.setattr("edge_tts.Communicate", FakeCommunicate)
    svc = TTSService()
    first = await svc.synthesize("Xin chào", "vi")
    second = await svc.synthesize("Xin chào", "vi")
    assert (first.cache_hit, second.cache_hit) == (False, True)
    assert calls == [("Xin chào", "vi-VN-HoaiMyNeural")]  # lần 2: zero cost
    assert first.url == f"/static/audio/{cache_key('Xin chào', 'vi')}.mp3"
    assert [p.suffix for p in tmp_path.iterdir()] == [".mp3"]  # không để lại .tmp


async def test_tts_concurrent_same_text_generates_once(tmp_path, monkeypatch):
    monkeypatch.setattr(tts_module, "AUDIO_DIR", tmp_path)
    calls = []

    class SlowCommunicate:
        def __init__(self, text, voice): ...

        async def save(self, path):
            calls.append(path)
            await asyncio.sleep(0.05)
            open(path, "wb").write(b"mp3")

    monkeypatch.setattr("edge_tts.Communicate", SlowCommunicate)
    svc = TTSService()
    results = await asyncio.gather(*[svc.synthesize("cùng một câu", "en") for _ in range(5)])
    assert len(calls) == 1 and sorted(r.cache_hit for r in results) == [False] + [True] * 4
    assert svc._locks == {}  # không rò khoá


async def test_tts_retries_then_fails_cleanly(tmp_path, monkeypatch):
    monkeypatch.setattr(tts_module, "AUDIO_DIR", tmp_path)
    monkeypatch.setattr(tts_module, "RETRY_BASE_DELAY", 0)
    attempts = []

    class Boom:
        def __init__(self, text, voice): ...

        async def save(self, path):
            attempts.append(1)
            raise ConnectionError("net down")

    monkeypatch.setattr("edge_tts.Communicate", Boom)
    with pytest.raises(RuntimeError):
        await TTSService().synthesize("lỗi mạng", "ko")
    assert len(attempts) == tts_module.NETWORK_RETRIES and list(tmp_path.iterdir()) == []


async def test_translate_maps_zh_code_and_vi_passthrough(monkeypatch):
    seen = []

    class FakeGT:
        def __init__(self, source, target):
            self.target = target

        def translate(self, text):
            seen.append(self.target)
            return f"<{self.target}>{text}"

    monkeypatch.setattr("deep_translator.GoogleTranslator", FakeGT)
    svc = TTSService()
    assert await svc.translate("món ngon", "vi") == "món ngon"
    assert await svc.translate("món ngon", "zh") == "<zh-CN>món ngon"
    assert await svc.translate("món ngon", "ja") == "<ja>món ngon"
    assert seen == ["zh-CN", "ja"]
    with pytest.raises(ValueError):
        await svc.translate("x", "fr")


# ---------------------------------------------------------------- Task 3.8: AudioTaskManager
async def test_task_generates_all_five_languages(client, manager, fake_tts):
    poi_id = await make_poi()
    task_id = await manager.enqueue_poi_audio_task(poi_id)
    t = await wait_status(task_id, "completed")
    assert (t["done"], t["total"], t["poi_name"]) == (5, 5, "Ốc Oanh")
    locs = {l["lang"]: l async for l in database.get_db()["poi_localizations"].find({"poi_id": ObjectId(poi_id)})}
    assert set(locs) == set(ALL_LANGS)
    assert all(l["audio_url"].endswith(".mp3") and l["audio_status"] == "completed" for l in locs.values())
    assert locs["en"]["description"].startswith("[en] ")
    assert (await database.get_db()["system_meta"].find_one({"_id": "dataset"}))["version"] == 1


async def test_existing_translation_is_kept_not_overwritten(client, manager, fake_tts):
    poi_id = await make_poi()
    poi = await database.get_db()["poi"].find_one({"_id": ObjectId(poi_id)})
    await database.get_db()["poi_localizations"].insert_one(
        {"poi_id": ObjectId(poi_id), "lang": "en", "title": "Oanh Snail",
         "description": "Hand-written English.",
         "source_hash": source_fingerprint(poi["name"], poi["original_description"]),
         "translation_origin": "manual"}
    )
    await wait_status(await manager.enqueue_poi_audio_task(poi_id, ["en"]), "completed")
    en = await database.get_db()["poi_localizations"].find_one({"poi_id": ObjectId(poi_id), "lang": "en"})
    assert en["description"] == "Hand-written English." and en["title"] == "Oanh Snail" and en["audio_url"]


async def test_semaphore_limits_to_three_concurrent(client, manager, fake_tts):
    fake_tts.delay = 0.03
    ids = [await manager.enqueue_poi_audio_task(await make_poi(f"Quán {i}"), ["en"]) for i in range(8)]
    for i in ids:
        await wait_status(i, "completed", timeout=5)
    assert fake_tts.max_active == 3


async def test_pause_resume_continues_from_checkpoint(client, manager, fake_tts):
    fake_tts.gate = asyncio.Event()
    task_id = await manager.enqueue_poi_audio_task(await make_poi())
    await wait_status(task_id, "running")
    await asyncio.sleep(0.05)  # worker đang kẹt ở ngôn ngữ đầu tiên
    assert (await manager.control(task_id, "pause"))["status"] == "paused"
    fake_tts.gate.set()  # ngôn ngữ đang làm dở xong, nhưng worker phải dừng ở ranh giới
    await asyncio.sleep(0.1)
    paused = await audio_task_store.get(task_id)
    assert paused["status"] == "paused" and paused["done"] == 1 and len(fake_tts.synth_calls) == 1
    assert (await manager.control(task_id, "resume"))["status"] == "queued"
    done = await wait_status(task_id, "completed")
    assert done["done"] == 5 and fake_tts.synth_calls == ALL_LANGS  # không làm lại ngôn ngữ đã xong


async def test_cancel_is_not_overwritten_by_completion(client, manager, fake_tts):
    fake_tts.gate = asyncio.Event()
    task_id = await manager.enqueue_poi_audio_task(await make_poi(), ["en"])  # 1 ngôn ngữ: lần ghi cuối là "completed"
    await wait_status(task_id, "running")
    await manager.control(task_id, "cancel")
    fake_tts.gate.set()
    await asyncio.sleep(0.1)
    assert (await audio_task_store.get(task_id))["status"] == "cancelled"


async def test_invalid_transitions_and_unknown_task(client, manager, fake_tts):
    task_id = await manager.enqueue_poi_audio_task(await make_poi(), ["en"])
    await wait_status(task_id, "completed")
    for action in ("pause", "resume", "cancel"):
        with pytest.raises(ValueError):
            await manager.control(task_id, action)
    assert await manager.control(str(ObjectId()), "pause") is None


async def test_failure_marks_failed_and_resume_retries(client, manager, monkeypatch):
    attempts = {"n": 0}

    class Flaky(FakeTTS):
        async def translate(self, text, lang):
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise RuntimeError("Google Translate rate limit")
            return await super().translate(text, lang)

    monkeypatch.setattr("app.modules.audio.task_manager.tts_service", Flaky())
    task_id = await manager.enqueue_poi_audio_task(await make_poi(), ["vi", "en"])
    failed = await wait_status(task_id, "failed")
    assert "rate limit" in failed["error"] and failed["done"] == 1
    await manager.control(task_id, "resume")
    assert (await wait_status(task_id, "completed"))["done"] == 2


async def test_enqueue_validation_and_dedupe(client, manager, fake_tts):
    fake_tts.gate = asyncio.Event()
    for bad in ("nope", str(ObjectId())):
        with pytest.raises(ValueError):
            await manager.enqueue_poi_audio_task(bad)
    poi_id = await make_poi()
    with pytest.raises(ValueError):
        await manager.enqueue_poi_audio_task(poi_id, ["fr"])
    first = await manager.enqueue_poi_audio_task(poi_id, ["en"])
    from app.modules.audio.task_manager import ActiveTaskExists

    with pytest.raises(ActiveTaskExists) as exc:
        await manager.enqueue_poi_audio_task(poi_id)
    assert exc.value.task_id == first
    fake_tts.gate.set()


async def test_missing_description_fails_gracefully(client, manager, fake_tts):
    res = await database.get_db()["poi"].insert_one({"name": "Không mô tả"})
    task_id = await manager.enqueue_poi_audio_task(str(res.inserted_id))
    assert "Missing Vietnamese description" in (await wait_status(task_id, "failed"))["error"]


async def test_recovery_after_restart_skips_finished_languages(client, manager, fake_tts):
    poi_id = await make_poi()
    # Mô phỏng server chết giữa chừng: đang `running`, đã xong 2/5 ngôn ngữ; kèm 1 tác vụ paused (không được chạy lại).
    running = await audio_task_store.create(poi_id, "Ốc Oanh", ALL_LANGS)
    await audio_task_store.update(
        running, status="running", done=2,
        source_hash=source_fingerprint("Ốc Oanh", "Quán ốc nổi tiếng Vĩnh Khánh."),
    )
    paused = await audio_task_store.create(poi_id, "Ốc Oanh", ["en"])
    await audio_task_store.update(paused, status="paused")
    assert await manager.recover() == 1
    done = await wait_status(running, "completed")
    assert done["done"] == 5 and fake_tts.synth_calls == ALL_LANGS[2:] and "recovered_at" in done
    assert (await audio_task_store.get(paused))["status"] == "paused"




async def test_legacy_checkpoint_restarts_languages_without_provenance(client, manager, fake_tts):
    poi_id = await make_poi()
    task_id = await audio_task_store.create(poi_id, "Ốc Oanh", ["vi", "en"])
    await audio_task_store.update(task_id, status="running", done=1)  # old schema, no source_hash
    assert await manager.recover() == 1
    completed = await wait_status(task_id, "completed")
    assert completed["done"] == 2
    assert fake_tts.synth_calls == ["vi", "en"]

async def test_recovery_purges_old_finished_tasks(client, manager, fake_tts):
    from datetime import datetime, timedelta, timezone

    old = await audio_task_store.create("x", "Old", ["en"])
    await audio_task_store.update(old, status="completed")
    await database.get_db()["audio_tasks"].update_one(
        {"_id": ObjectId(old)}, {"$set": {"updated_at": datetime.now(timezone.utc) - timedelta(days=30)}}
    )
    await manager.recover()
    assert await audio_task_store.get(old) is None


# ---------------------------------------------------------------- Task 3.9: SSE
class FakeRequest:
    def __init__(self, disconnect_after: int):
        self.calls = 0
        self.limit = disconnect_after

    async def is_disconnected(self):
        self.calls += 1
        return self.calls > self.limit


async def test_sse_pushes_snapshot_then_change_then_keepalive(client):
    req = FakeRequest(disconnect_after=3)
    gen = audio_tasks_event_stream(req, interval=0.05)
    assert await gen.__anext__() == "retry: 3000\n\n"
    first = await gen.__anext__()
    assert first.startswith("event: tasks\ndata: ") and json.loads(first.split("data: ")[1]) == []
    task_id = await audio_task_store.create("p", "Ốc Oanh", ["en", "ja"])  # thay đổi → đẩy ngay
    second = await gen.__anext__()
    payload = json.loads(second.split("data: ")[1])
    assert second.startswith("event: tasks") and payload[0]["id"] == task_id and payload[0]["poi_name"] == "Ốc Oanh"
    assert await gen.__anext__() == ": keepalive\n\n"  # không đổi → keepalive
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()
    assert audio_task_store._subscribers == set()  # ngắt kết nối thì huỷ đăng ký


# ---------------------------------------------------------------- Endpoints
async def test_endpoints_require_auth_and_permission(client):
    assert (await client.get(TASKS)).status_code == 401
    assert (await client.get(TASKS + "/stream")).status_code == 401
    await database.get_db()["users"].insert_one(
        {"email": "u@t.vn", "password_hash": hash_password("Passw0rd!"), "role": "user", "is_active": True}
    )
    await client.post(LOGIN, json={"email": "u@t.vn", "password": "Passw0rd!"})
    assert (await client.get(TASKS)).status_code == 403
    assert (await client.post(TASKS, json={"poi_id": "x"})).status_code == 403
    assert (await client.post(TASKS + "/abc/pause")).status_code == 403


async def test_endpoint_flow_create_control_audit(client, fake_tts):
    await admin_login(client)
    fake_tts.gate = asyncio.Event()
    poi_id = await make_poi()
    assert (await client.post(TASKS, json={"poi_id": "bad"})).status_code == 422
    assert (await client.post(TASKS, json={"poi_id": poi_id, "languages": ["fr"]})).status_code == 422
    r = await client.post(TASKS, json={"poi_id": poi_id, "languages": ["en", "ja"]})
    assert r.status_code == 202 and r.json()["status"] == "queued"
    task_id = r.json()["id"]
    dup = await client.post(TASKS, json={"poi_id": poi_id})
    assert dup.status_code == 409 and dup.json()["detail"]["task_id"] == task_id
    assert (await client.post(f"{TASKS}/{task_id}/explode")).status_code == 422
    assert (await client.post(f"{TASKS}/{ObjectId()}/pause")).status_code == 404
    assert (await client.post(f"{TASKS}/{task_id}/pause")).json()["status"] == "paused"
    assert (await client.post(f"{TASKS}/{task_id}/pause")).status_code == 409
    assert (await client.post(f"{TASKS}/{task_id}/cancel")).json()["status"] == "cancelled"
    items = (await client.get(TASKS)).json()["items"]
    assert items[0]["id"] == task_id and items[0]["status"] == "cancelled"
    actions = {a["action"] async for a in database.get_db()["audit_logs"].find({"action": {"$regex": "^audio\\."}})}
    assert actions == {"audio.task_enqueue", "audio.task_pause", "audio.task_cancel"}
    fake_tts.gate.set()

# --------------------------------------------------------- Regression tests (Audio 3.7–3.9)
async def test_pause_on_final_language_never_auto_completes(client, manager, fake_tts):
    """Pause while final audio is generating; completion must wait for explicit Resume."""
    fake_tts.gate = asyncio.Event()
    task_id = await manager.enqueue_poi_audio_task(await make_poi(), ["en"])
    await wait_status(task_id, "running")
    await asyncio.sleep(0.03)
    await manager.control(task_id, "pause")
    fake_tts.gate.set()
    await asyncio.sleep(0.08)
    paused = await audio_task_store.get(task_id)
    assert paused["status"] == "paused" and paused["done"] == 1
    assert await database.get_db()["system_meta"].find_one({"_id": "dataset"}) is None
    await manager.control(task_id, "resume")
    completed = await wait_status(task_id, "completed")
    assert completed["done"] == 1
    assert (await database.get_db()["system_meta"].find_one({"_id": "dataset"}))["version"] == 1
    assert fake_tts.synth_calls == ["en"]


async def test_cancel_interrupts_in_flight_audio_without_writing_localization(client, manager, fake_tts):
    fake_tts.gate = asyncio.Event()
    poi_id = await make_poi()
    task_id = await manager.enqueue_poi_audio_task(poi_id, ["en"])
    await wait_status(task_id, "running")
    await asyncio.sleep(0.03)
    await manager.control(task_id, "cancel")
    await asyncio.sleep(0.05)
    assert (await audio_task_store.get(task_id))["status"] == "cancelled"
    assert await database.get_db()["poi_localizations"].find_one({"poi_id": ObjectId(poi_id), "lang": "en"}) is None
    fake_tts.gate.set()


async def test_double_enqueue_same_poi_is_serialized(client, manager, fake_tts):
    """Two simultaneous POSTs must not pass 'find active' before either creates its task."""
    from app.modules.audio.task_manager import ActiveTaskExists

    fake_tts.gate = asyncio.Event()
    poi_id = await make_poi()
    results = await asyncio.gather(
        manager.enqueue_poi_audio_task(poi_id, ["en"]),
        manager.enqueue_poi_audio_task(poi_id, ["ja"]),
        return_exceptions=True,
    )
    assert len([r for r in results if isinstance(r, str)]) == 1
    assert len([r for r in results if isinstance(r, ActiveTaskExists)]) == 1
    with pytest.raises(ValueError):
        await manager.enqueue_poi_audio_task(poi_id, [])
    fake_tts.gate.set()


async def test_two_service_instances_use_distinct_temp_files(tmp_path, monkeypatch):
    """In separate workers, simultaneous MP3 creation must not overwrite the same .tmp file."""
    monkeypatch.setattr(tts_module, "AUDIO_DIR", tmp_path)
    paths = []
    release = asyncio.Event()

    class ConcurrentCommunicate:
        def __init__(self, text, voice):
            pass

        async def save(self, path):
            paths.append(path)
            if len(paths) == 2:
                release.set()
            await asyncio.wait_for(release.wait(), timeout=1)
            with open(path, "wb") as audio:
                audio.write(b"mp3")

    monkeypatch.setattr("edge_tts.Communicate", ConcurrentCommunicate)
    await asyncio.gather(
        TTSService().synthesize("Hai tiến trình", "ja"),
        TTSService().synthesize("Hai tiến trình", "ja"),
    )
    assert len(paths) == 2 and len(set(paths)) == 2
    assert list(p.name for p in tmp_path.iterdir()) == [f"{cache_key('Hai tiến trình', 'ja')}.mp3"]


async def test_audio_endpoint_rejects_bad_payload_schema(client):
    await admin_login(client)
    for body in ({"poi_id": "x"}, {"poi_id": "a" * 24, "languages": []},
                 {"poi_id": "a" * 24, "languages": ["fr"]},
                 {"poi_id": "a" * 24, "languages": "en"}):
        assert (await client.post(TASKS, json=body)).status_code == 422


async def test_tts_translates_new_poi_title_before_english_gate(client, manager, fake_tts):
    poi_id = await make_poi("Ốc Oanh", "Ốc ngon mỗi ngày")
    await wait_status(await manager.enqueue_poi_audio_task(poi_id, ["en"]), "completed")
    en = await database.get_db()["poi_localizations"].find_one({
        "poi_id": ObjectId(poi_id), "lang": "en"
    })
    assert en["title"] == "[en] Ốc Oanh"
    assert en["description"] == "[en] Ốc ngon mỗi ngày"
    from app.modules.admin.poi_management import gate_for
    assert (await gate_for(ObjectId(poi_id)))["ready"] is True


async def test_tts_does_not_overwrite_concurrent_admin_translation(client, manager, fake_tts):
    poi_id = await make_poi()
    fake_tts.gate = asyncio.Event()
    task_id = await manager.enqueue_poi_audio_task(poi_id, ["en"])
    await wait_status(task_id, "running")
    # Wait until the worker is in synthesize (after reading the old text).
    for _ in range(300):
        if fake_tts.synth_calls:
            break
        await asyncio.sleep(.01)
    assert fake_tts.synth_calls
    await database.get_db()["poi_localizations"].insert_one({
        "poi_id": ObjectId(poi_id), "lang": "en",
        "title": "My approved title", "description": "My approved description",
    })
    fake_tts.gate.set()
    task = await wait_status(task_id, "failed")
    assert "Localization was edited" in task.get("error", "")
    en = await database.get_db()["poi_localizations"].find_one({
        "poi_id": ObjectId(poi_id), "lang": "en"
    })
    assert en["title"] == "My approved title"
    assert en["description"] == "My approved description"
    assert not en.get("audio_url")


# --------------------------------------------------------- Data freshness / multi-worker regressions
async def test_stale_localization_is_retranslated_when_source_changed(client, manager, fake_tts):
    poi_id = await make_poi(desc="Mô tả cũ")
    db = database.get_db()
    first = await manager.enqueue_poi_audio_task(poi_id, ["en"])
    await wait_status(first, "completed")
    old = await db["poi_localizations"].find_one({"poi_id": ObjectId(poi_id), "lang": "en"})
    assert "Mô tả cũ" in old["description"]
    await db["poi"].update_one({"_id": ObjectId(poi_id)}, {"$set": {"original_description": "Mô tả hoàn toàn mới"}})
    # Deliberately bypass Admin invalidation to prove source-hash checking independently.
    second = await manager.enqueue_poi_audio_task(poi_id, ["en"])
    await wait_status(second, "completed")
    new = await db["poi_localizations"].find_one({"poi_id": ObjectId(poi_id), "lang": "en"})
    assert "Mô tả hoàn toàn mới" in new["description"]
    assert new["description"] != old["description"]
    assert new["source_hash"] != old["source_hash"]


async def test_admin_edit_invalidates_audio_in_all_five_languages(client, manager, fake_tts):
    from app.modules.admin.poi_management import update_poi
    from app.modules.admin.schemas import POIUpdateRequest

    poi_id = await make_poi()
    await wait_status(await manager.enqueue_poi_audio_task(poi_id), "completed")
    db = database.get_db()
    before = [l async for l in db["poi_localizations"].find({"poi_id": ObjectId(poi_id)})]
    assert set(l["lang"] for l in before) == set(ALL_LANGS)
    await update_poi(poi_id, POIUpdateRequest(original_description="Mô tả mới cho quán"),
                     {"id": "test-admin"}, "127.0.0.1")
    after = {l["lang"]: l async for l in db["poi_localizations"].find({"poi_id": ObjectId(poi_id)})}
    assert after["vi"]["description"] == "Mô tả mới cho quán"
    assert all(l["audio_url"] is None and l["audio_status"] == "pending" for l in after.values())
    assert all("source_hash" not in after[lang] for lang in ("en", "zh", "ja", "ko"))
    assert after["vi"]["source_hash"] == source_fingerprint("Ốc Oanh", "Mô tả mới cho quán")


async def test_expired_claim_recovered_but_live_owner_not_stolen(client, manager, fake_tts):
    from datetime import timedelta
    from app.modules.audio.task_store import now

    poi_id = await make_poi()
    task_id = await audio_task_store.create(poi_id, "Ốc Oanh", ["vi"])
    future = now() + timedelta(minutes=10)
    await database.get_db()["audio_tasks"].update_one(
        {"_id": ObjectId(task_id)},
        {"$set": {"status": "running", "lease_token": "different-process", "lease_until": future}},
    )
    assert await manager.recover() == 0
    assert (await audio_task_store.get(task_id))["status"] == "running"
    await database.get_db()["audio_tasks"].update_one(
        {"_id": ObjectId(task_id)}, {"$set": {"lease_until": now() - timedelta(minutes=1)}},
    )
    assert await manager.recover() == 1
    await wait_status(task_id, "completed")


async def test_global_three_slots_across_two_managers(client, fake_tts):
    """Separate process-like managers share MongoDB global slot allocation."""
    fake_tts.delay = 0.04
    first = AudioTaskManager()
    second = AudioTaskManager()
    try:
        poi_ids = [await make_poi(f"Quán toàn cục {i}") for i in range(8)]
        ids = await asyncio.gather(*[
            (first if i % 2 else second).enqueue_poi_audio_task(pid, ["en"])
            for i, pid in enumerate(poi_ids)
        ])
        for task_id in ids:
            await wait_status(task_id, "completed", timeout=8)
        assert fake_tts.max_active <= 3
        from app.modules.audio.task_store import now
        for _ in range(100):
            active_slots = await database.get_db()["audio_worker_slots"].count_documents(
                {"expires_at": {"$gt": now()}}
            )
            if active_slots == 0:
                break
            await asyncio.sleep(0.01)
        assert active_slots == 0
    finally:
        await first.shutdown()
        await second.shutdown()


async def test_idle_audio_recovery_does_not_spam_info(manager, caplog):
    """A supervisor tick with no work is normal, not an INFO event every 15s."""
    with caplog.at_level(logging.INFO, logger="quan4.audio.tasks"):
        assert await manager.recover() == 0
        assert await manager.recover() == 0
    assert not [rec for rec in caplog.records if rec.levelno >= logging.INFO
                and "Audio recovery:" in rec.getMessage()]
