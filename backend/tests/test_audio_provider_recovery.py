import pytest

from app.modules.audio import service


@pytest.mark.asyncio
async def test_google_rate_limit_uses_gemini_and_bypasses_cooldown(monkeypatch):
    from deep_translator.exceptions import TooManyRequests

    calls = []

    class LimitedGoogle:
        def __init__(self, **kwargs):
            pass

        def translate(self, text):
            calls.append("google")
            raise TooManyRequests()

    async def translate_gemini(self, chunk, target):
        calls.append(target)
        return f"Translated {chunk}"

    monkeypatch.setattr(service, "_translation_pacer", service.TranslationPacer())
    monkeypatch.setattr("deep_translator.GoogleTranslator", LimitedGoogle)
    monkeypatch.setattr(service.TTSService, "_translate_gemini", translate_gemini)

    tts = service.TTSService()
    assert await tts._translate_free_with_fallbacks("Tên quán", "en", "en") == "Translated Tên quán"
    assert await tts._translate_free_with_fallbacks("Mô tả", "en", "en") == "Translated Mô tả"
    assert calls == ["google", "en", "en"]

@pytest.mark.asyncio
async def test_speech_retry_preserves_completed_languages(client, monkeypatch):
    import asyncio

    from app.core import database
    from app.modules.audio import task_manager
    from app.modules.audio.task_store import audio_task_store

    class RecoveringSpeech:
        def __init__(self):
            self.calls = []

        async def translate(self, text, lang):
            return f"{lang}: {text}"

        async def synthesize(self, text, lang):
            self.calls.append(lang)
            if self.calls == ["vi", "en"]:
                raise service.SpeechTemporarilyUnavailable("Speech temporarily unavailable")
            return service.SynthResult("/static/audio/test.mp3", False)

    provider = RecoveringSpeech()
    monkeypatch.setattr(task_manager, "tts_service", provider)
    poi = await database.get_db()["poi"].insert_one({"name": "Quán thử", "original_description": "Mô tả thử"})
    manager = task_manager.AudioTaskManager()

    async def wait_for(predicate):
        for _ in range(300):
            task = await audio_task_store.get(task_id)
            if predicate(task):
                return task
            await asyncio.sleep(0.01)
        pytest.fail("Audio task did not reach the expected state")

    try:
        task_id = await manager.enqueue_poi_audio_task(str(poi.inserted_id), ["vi", "en"])
        pending = await wait_for(lambda task: task.get("retry_at"))
        assert (pending["status"], pending["retry_kind"], pending["done"]) == ("queued", "speech", 1)
        await manager.control(task_id, "retry")
        completed = await wait_for(lambda task: task["status"] == "completed")
        assert completed["done"] == 2
        assert provider.calls == ["vi", "en", "en"]
        assert "retry_kind" not in completed
    finally:
        await manager.shutdown()
