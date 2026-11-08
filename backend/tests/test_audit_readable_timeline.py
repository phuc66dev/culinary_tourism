"""Audit timeline snapshots: identify actors/targets after deletion, with safe diffs.

Run: python -m pytest -q tests/test_audit_readable_timeline.py
"""
import pytest


@pytest.mark.asyncio
async def test_user_audit_snapshots_survive_soft_delete(client, admin_creds):
    login = await client.post('/api/v1/admin/auth/login', json=admin_creds)
    assert login.status_code == 200, login.text

    created = await client.post('/api/v1/admin/users', json={
        'email': 'audit-staff@example.com',
        'full_name': 'Nhân viên kiểm thử',
        'password': 'SecurePassword123!',
        'role': 'user',
        'is_active': True,
    })
    assert created.status_code == 201, created.text
    uid = created.json()['id']

    updated = await client.patch(f'/api/v1/admin/users/{uid}', json={
        'full_name': 'Nhân viên đã sửa', 'is_active': False,
    })
    assert updated.status_code == 200, updated.text

    deleted = await client.delete(f'/api/v1/admin/users/{uid}')
    assert deleted.status_code == 200, deleted.text

    events = await client.get('/api/v1/admin/audit-logs', params={'q': 'Nhân viên đã sửa'})
    assert events.status_code == 200, events.text
    logs = events.json()['items']
    soft_delete = next(event for event in logs if event['action'] == 'user.soft_delete')
    assert soft_delete['target_name'] == 'Nhân viên đã sửa'
    assert soft_delete['target_email'] == 'audit-staff@example.com'
    assert soft_delete['actor_email'] == admin_creds['email']
    assert soft_delete['details']['before'] == {'is_active': False}
    assert soft_delete['details']['after'] == {'is_active': False}

    all_logs = (await client.get('/api/v1/admin/audit-logs', params={'resource': f'user:{uid}'})).json()['items']
    changed = next(event for event in all_logs if event['action'] == 'user.update')
    assert changed['details']['before'] == {'full_name': 'Nhân viên kiểm thử', 'is_active': True}
    assert changed['details']['after'] == {'full_name': 'Nhân viên đã sửa', 'is_active': False}
    assert changed['target_email'] == 'audit-staff@example.com'
    # Audit details may include non-sensitive state but must never contain a password.
    assert 'password' not in str(all_logs).lower()


@pytest.mark.asyncio
async def test_poi_deleted_audit_keeps_name(client, admin_creds):
    assert (await client.post('/api/v1/admin/auth/login', json=admin_creds)).status_code == 200
    created = await client.post('/api/v1/admin/pois', json={
        'name': 'Ốc Test Nhật Ký', 'address': '7 Vĩnh Khánh', 'ward': 'Phường 8',
        'category': 'street_food',
        'location': {'type': 'Point', 'coordinates': [106.702, 10.758]},
        'original_description': 'Mô tả quán kiểm thử', 'images': [],
    })
    assert created.status_code == 201, created.text
    poi_id = created.json()['id']
    assert (await client.delete(f'/api/v1/admin/pois/{poi_id}')).status_code == 200
    response = await client.get('/api/v1/admin/audit-logs', params={'action': 'poi.delete', 'q': 'Ốc Test Nhật Ký'})
    assert response.status_code == 200, response.text
    assert response.json()['items'][0]['target_name'] == 'Ốc Test Nhật Ký'
