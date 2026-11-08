"""Optional REAL MongoDB replica-set transaction integration smoke test.

RUN_MONGO_TX_INTEGRATION=1 pytest -q tests/test_mongo_transaction_integration.py
The normal test suite does not require a database server.
"""
import os
import uuid
from contextlib import suppress
import pytest

pytestmark = pytest.mark.skipif(os.getenv('RUN_MONGO_TX_INTEGRATION') != '1',
    reason='Requires a real MongoDB replica set; set RUN_MONGO_TX_INTEGRATION=1')


@pytest.mark.asyncio
async def test_rollback_across_collections(monkeypatch):
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.core import database
    from app.core.config import settings

    client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    name = f'quan4_transaction_smoke_{uuid.uuid4().hex[:10]}'
    db = client[name]
    monkeypatch.setattr(database, 'mongo_client', client)
    monkeypatch.setattr(database, 'db', db)
    try:
        await db['one'].insert_one({'_id': 'seed'})  # create collections before transaction
        await db['two'].insert_one({'_id': 'seed'})
        with pytest.raises(RuntimeError, match='rollback'):
            async with database.mongo_transaction() as tx:
                await db['one'].insert_one({'_id': 'rollback-a'}, session=tx)
                await db['two'].insert_one({'_id': 'rollback-b'}, session=tx)
                raise RuntimeError('rollback')
        assert await db['one'].count_documents({'_id': 'rollback-a'}) == 0
        assert await db['two'].count_documents({'_id': 'rollback-b'}) == 0
        async with database.mongo_transaction() as tx:
            await db['one'].insert_one({'_id': 'commit-a'}, session=tx)
            await db['two'].insert_one({'_id': 'commit-b'}, session=tx)
        assert await db['one'].count_documents({'_id': 'commit-a'}) == 1
        assert await db['two'].count_documents({'_id': 'commit-b'}) == 1
    finally:
        with suppress(Exception):
            await client.drop_database(name)
        client.close()

@pytest.mark.asyncio
async def test_audio_completion_and_dataset_version_commit_or_rollback_together(monkeypatch):
    """Real replica-set test: version update failure MUST roll back task completion."""
    from datetime import timedelta
    from motor.motor_asyncio import AsyncIOMotorClient
    from bson import ObjectId
    from app.core import database
    from app.core.config import settings
    from app.modules.audio.task_manager import AudioTaskManager
    from app.modules.audio.task_store import now

    client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    db_name = f'quan4_audio_atomic_{uuid.uuid4().hex[:10]}'
    db = client[db_name]
    monkeypatch.setattr(database, 'mongo_client', client)
    monkeypatch.setattr(database, 'db', db)
    manager = AudioTaskManager()
    task_id = str(ObjectId())
    try:
        await db['audio_tasks'].insert_one({
            '_id': ObjectId(task_id), 'status': 'running', 'lease_token': 'test-token',
            'lease_until': now() + timedelta(minutes=5), 'done': 1, 'total': 1,
        })
        await db['system_meta'].insert_many([
            {'_id': 'dataset', 'version': 1}, {'_id': 'collision', 'version': 2},
        ])
        await db['system_meta'].create_index('version', unique=True)
        with pytest.raises(Exception):
            # Duplicate-key on version 2 forces transaction abort.
            await manager._finish_transaction(task_id, 'test-token')
        assert (await db['audio_tasks'].find_one({'_id': ObjectId(task_id)}))['status'] == 'running'
        assert (await db['system_meta'].find_one({'_id': 'dataset'}))['version'] == 1
        await db['system_meta'].delete_one({'_id': 'collision'})
        assert await manager._finish_transaction(task_id, 'test-token') is True
        assert (await db['audio_tasks'].find_one({'_id': ObjectId(task_id)}))['status'] == 'completed'
        assert (await db['system_meta'].find_one({'_id': 'dataset'}))['version'] == 2
    finally:
        with suppress(Exception):
            await client.drop_database(db_name)
        client.close()


@pytest.mark.asyncio
async def test_audio_enqueue_rolls_back_if_audit_insert_fails(monkeypatch):
    """A real Mongo replica set must never commit an unaudited audio enqueue."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from bson import ObjectId
    from app.core import database
    from app.core.config import settings
    import app.modules.audio.task_manager as manager_module

    client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    db_name = f'quan4_audit_atomic_{uuid.uuid4().hex[:10]}'
    db = client[db_name]
    monkeypatch.setattr(database, 'mongo_client', client)
    monkeypatch.setattr(database, 'db', db)
    manager = manager_module.AudioTaskManager()
    monkeypatch.setattr(manager, '_start', lambda _id: None)
    poi_id, admin_id = ObjectId(), ObjectId()
    try:
        await db['poi'].insert_one({'_id': poi_id, 'name': 'Quán thử'})
        await db['users'].insert_one({'_id': admin_id, 'email': 'audit@test.local', 'role': 'super_admin'})

        async def unavailable(*args, **kwargs):
            raise RuntimeError('audit write unavailable')

        actual = manager_module.write_audit_event
        monkeypatch.setattr(manager_module, 'write_audit_event', unavailable)
        with pytest.raises(RuntimeError, match='audit write unavailable'):
            await manager.enqueue_poi_audio_task(str(poi_id), ['vi'], actor_id=str(admin_id), actor_ip='127.0.0.1')
        assert await db['audio_tasks'].count_documents({}) == 0
        assert await db['audit_logs'].count_documents({}) == 0

        monkeypatch.setattr(manager_module, 'write_audit_event', actual)
        task_id = await manager.enqueue_poi_audio_task(str(poi_id), ['vi'], actor_id=str(admin_id), actor_ip='127.0.0.1')
        assert await db['audio_tasks'].count_documents({}) == 1
        assert await db['audit_logs'].count_documents({'resource': f'audio_task:{task_id}'}) == 1
    finally:
        with suppress(Exception):
            await client.drop_database(db_name)
        client.close()
