"""Regression: Google 429 retry + cached translation + Vietnamese accent-insensitive POI search.

Run: python -m pytest -q tests/test_translation_limits_and_accent_search.py
Tests use mocked Google requests and mongomock-motor; no live Google needed.
"""
import asyncio
import re
from datetime import timedelta

import pytest
from bson import ObjectId
from deep_translator.exceptions import TooManyRequests

from app.core import database
from app.modules.admin.poi_management import vietnamese_search_regex
from app.modules.audio import service as translation_module
from app.modules.audio.service import TTSService, TranslationRateLimited
from app.modules.audio.task_manager import AudioTaskManager
from app.modules.audio.task_store import audio_task_store, now


@pytest.mark.parametrize("q, name, matches", [
    ("trang", "Bánh Tráng Nướng", True),
    ("trang", "Bánh Trắng", True),
    ("tráng", "Quán Trang", True),
    ("banh mi", "Bánh Mì Ngon", True),
    ("dang", "Quán Đặng", True),
    ("trang", "Bún Bò", False),
    (".*", "Bánh Tráng", False),
])
def test_search_regex_is_accent_insensitive_and_literal(q, name, matches):
    assert bool(re.search(vietnamese_search_regex(q), name, re.IGNORECASE)) is matches


@pytest.mark.asyncio
async def test_admin_poi_name_search_without_accents(client, admin_creds):
    response = await client.post('/api/v1/admin/auth/login', json=admin_creds)
    assert response.status_code == 200
    for name in ("Bánh Tráng Nướng", "Quán Trắng", "Bánh Mì"):
        data = {
            "name": name, "address": "Vĩnh Khánh, Quận 4", "ward": "Phường 8",
            "category": "street_food", "location": {"type": "Point", "coordinates": [106.704, 10.757]},
            "original_description": "Đồ ăn ngon.", "images": [],
        }
        created = await client.post('/api/v1/admin/pois', json=data)
        assert created.status_code == 201, created.text
    matching = await client.get('/api/v1/admin/pois', params={'q': 'trang', 'limit': 1})
    assert matching.status_code == 200, matching.text
    assert matching.json()['total'] == 2
    another_page = await client.get('/api/v1/admin/pois', params={'q': 'trang', 'limit': 1, 'skip': 1})
    assert another_page.json()['total'] == 2
    assert len(another_page.json()['items']) == 1
    all_accented = await client.get('/api/v1/admin/pois', params={'q': 'tráng'})
    assert all_accented.json()['total'] == 2


@pytest.mark.asyncio
async def test_google_429_is_retryable_and_success_is_cached(client, monkeypatch):
    monkeypatch.setattr(translation_module, 'TRANSLATION_MIN_INTERVAL', 0)
    monkeypatch.setattr(translation_module, '_translation_pacer', translation_module.TranslationPacer())
    attempts = []

    class FakeGoogle:
        def __init__(self, source, target):
            self.target = target

        def translate(self, text):
            attempts.append(self.target)
            if len(attempts) == 1:
                raise TooManyRequests()
            return 'Translated: ' + text

    monkeypatch.setattr('deep_translator.GoogleTranslator', FakeGoogle)
    svc = TTSService()
    with pytest.raises(TranslationRateLimited):
        await svc.translate('Quán hải sản', 'en')
    assert await svc.translate('Quán hải sản', 'en') == 'Translated: Quán hải sản'
    # New service instance shares MongoDB cache, so it must not call Google again.
    assert await TTSService().translate('Quán hải sản', 'en') == 'Translated: Quán hải sản'
    assert attempts == ['en', 'en']


@pytest.mark.asyncio
async def test_audio_queue_auto_resumes_after_google_429(client, monkeypatch):
    class FakeProvider:
        def __init__(self):
            self.rejected = False

        async def translate(self, text, lang):
            if lang == 'en' and not self.rejected:
                self.rejected = True
                raise TranslationRateLimited('Google Translate đang giới hạn yêu cầu')
            return text if lang == 'vi' else f'[{lang}] {text}'

        async def synthesize(self, text, lang):
            from app.modules.audio.service import SynthResult
            return SynthResult('/static/audio/fake.mp3', False)

    fake = FakeProvider()
    monkeypatch.setattr('app.modules.audio.task_manager.tts_service', fake)
    db = database.get_db()
    poi_id = (await db['poi'].insert_one({
        'name': 'Ốc Oanh', 'original_description': 'Ốc tươi mỗi ngày.', 'is_active': False,
    })).inserted_id
    manager = AudioTaskManager()
    try:
        task_id = await manager.enqueue_poi_audio_task(str(poi_id), ['vi', 'en', 'zh', 'ja', 'ko'])
        for _ in range(150):
            task = await audio_task_store.get(task_id)
            if task.get('retry_at'):
                break
            await asyncio.sleep(0.01)
        else:
            pytest.fail('429 did not schedule a retry')
        assert task['status'] == 'queued'
        assert task['done'] == 1
        assert task['translation_retries'] == 1
        assert await manager.recover() == 0  # not due: no busy looping
        await db['audio_tasks'].update_one({'_id': ObjectId(task_id)}, {
            '$set': {'retry_at': now() - timedelta(seconds=1)},
        })
        assert await manager.recover() >= 1
        for _ in range(300):
            task = await audio_task_store.get(task_id)
            if task['status'] == 'completed':
                break
            await asyncio.sleep(0.01)
        assert task['status'] == 'completed', task
        assert task['done'] == 5
        locs = {doc['lang'] async for doc in db['poi_localizations'].find({'poi_id': poi_id})}
        assert locs == {'vi', 'en', 'zh', 'ja', 'ko'}
    finally:
        await manager.shutdown()
