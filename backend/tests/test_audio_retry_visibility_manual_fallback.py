"""Regression tests for correct retry clocks, bounded retries and manual translation fallback.

Run: python -m pytest -q tests/test_audio_retry_visibility_manual_fallback.py
Requires the same mongomock-motor dependencies as tests/test_audio_tasks.py.
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.core import database
from app.modules.audio import task_manager as manager_module
from app.modules.audio.manual_translation import save_task_manual_translation
from app.modules.audio.service import SynthResult, TranslationRateLimited
from app.modules.audio.task_manager import AudioTaskManager
from app.modules.audio.task_store import audio_task_store, serialize, now


def test_mongodb_naive_utc_timestamp_serializes_as_utc():
    # Motor/PyMongo returns naive datetimes by default even when saved with timezone.utc.
    record = {
        '_id': ObjectId(), 'status': 'queued',
        'retry_at': datetime(2026, 10, 29, 11, 9, 16),
        'created_at': datetime(2026, 10, 29, 11, 0, tzinfo=timezone.utc),
    }
    item = serialize(record)
    assert datetime.fromisoformat(item['retry_at']).utcoffset() == timedelta(0)
    assert datetime.fromisoformat(item['created_at']).utcoffset() == timedelta(0)
    assert item['retry_at'].startswith('2026-10-29T11:09:16')
    assert manager_module.MAX_AUTO_TRANSLATION_RETRIES <= 3


@pytest.mark.asyncio
async def test_manual_translations_resume_audio_without_google(client, monkeypatch):
    class UnavailableGoogle:
        def __init__(self):
            self.calls = 0
            self.audio = []

        async def translate(self, text, lang):
            self.calls += 1
            raise TranslationRateLimited('Google 429')

        async def synthesize(self, text, lang):
            self.audio.append((lang, text))
            return SynthResult('/static/audio/demo.mp3', False)

    fake = UnavailableGoogle()
    monkeypatch.setattr(manager_module, 'tts_service', fake)
    db = database.get_db()
    pid = (await db['poi'].insert_one({
        'name': 'Ốc Oanh', 'original_description': 'Ốc tươi mỗi ngày', 'is_active': False,
    })).inserted_id
    manager = AudioTaskManager()
    try:
        tid = await manager.enqueue_poi_audio_task(str(pid), ['en', 'zh'])
        for _ in range(250):
            task = await audio_task_store.get(tid)
            if task.get('retry_at'):
                break
            await asyncio.sleep(0.01)
        assert task['status'] == 'queued'
        assert fake.calls == 1
        for lang, title, desc in [
            ('en', 'Fresh Sea Snails', 'Fresh seafood every day'),
            ('zh', '新鲜海鲜', '每日新鲜海鲜'),
        ]:
            r = await save_task_manual_translation(tid, lang, title, desc, str(ObjectId()), '127.0.0.1')
            assert r['status'] == 'paused'
        task = await audio_task_store.get(tid)
        assert task['status'] == 'paused'
        assert 'retry_at' not in task
        assert await manager.control(tid, 'resume')
        for _ in range(300):
            task = await audio_task_store.get(tid)
            if task['status'] == 'completed':
                break
            await asyncio.sleep(0.01)
        assert task['status'] == 'completed', task
        assert task['done'] == 2
        assert fake.calls == 1, 'manual translations must not call Google on resume'
        assert fake.audio == [('en', 'Fresh seafood every day'), ('zh', '每日新鲜海鲜')]
        locs = [x async for x in db['poi_localizations'].find({'poi_id': pid})]
        assert {x['lang']: x['translation_origin'] for x in locs} == {'en': 'manual', 'zh': 'manual'}
    finally:
        await manager.shutdown()


@pytest.mark.asyncio
async def test_manual_translation_rejects_completed_and_invalid_language(client):
    db = database.get_db()
    pid = (await db['poi'].insert_one({'name':'Quán', 'original_description':'Đồ ngon'})).inserted_id
    tid = await audio_task_store.create(str(pid), 'Quán', ['en'])
    with pytest.raises(HTTPException) as invalid:
        await save_task_manual_translation(tid, 'vi', 'Tên', 'Mô tả', str(ObjectId()))
    assert invalid.value.status_code == 422
    await audio_task_store.update(tid, status='completed', done=1)
    with pytest.raises(HTTPException) as completed:
        await save_task_manual_translation(tid, 'en', 'Title', 'Description', str(ObjectId()))
    assert completed.value.status_code == 409


@pytest.mark.asyncio
async def test_retry_now_bypasses_future_scheduled_time(client, monkeypatch):
    class FailsOnce:
        def __init__(self):
            self.attempts = 0

        async def translate(self, text, lang):
            self.attempts += 1
            if self.attempts == 1:
                raise TranslationRateLimited('429')
            return 'A translation'

        async def synthesize(self, text, lang):
            return SynthResult('/static/audio/demo.mp3', False)

    fake = FailsOnce()
    monkeypatch.setattr(manager_module, 'tts_service', fake)
    db = database.get_db()
    pid = (await db['poi'].insert_one({'name': 'Quán', 'original_description': 'Ngon', 'is_active': False})).inserted_id
    manager = AudioTaskManager()
    try:
        tid = await manager.enqueue_poi_audio_task(str(pid), ['en'])
        for _ in range(250):
            task = await audio_task_store.get(tid)
            if task.get('retry_at'):
                break
            await asyncio.sleep(0.01)
        assert task['retry_at'] > now()
        r = await manager.control(tid, 'retry')
        assert r['status'] == 'queued' or r['status'] == 'running' or r['status'] == 'completed'
        for _ in range(300):
            task = await audio_task_store.get(tid)
            if task['status'] == 'completed':
                break
            await asyncio.sleep(0.01)
        assert task['status'] == 'completed', task
    finally:
        await manager.shutdown()
