"""End-to-end contract tests using mongomock-motor (transactions are bypassed ONLY in APP_ENV=test).
Run with: cd backend && pip install -r requirements.txt -r requirements-dev.txt && pytest -q
"""
import pytest
from app.core import database

AUTH = '/api/v1/admin/auth'


async def login(client, creds):
    r = await client.post(f'{AUTH}/login', json=creds)
    assert r.status_code == 200, r.text
    return r.json()


async def change_default_password(client, creds):
    body = await login(client, creds)
    r = await client.post(f'{AUTH}/change-password', json={
        'current_password': creds['password'], 'new_password': 'NewSuperPassword#456'})
    assert r.status_code == 200, r.text
    return await login(client, {**creds, 'password': 'NewSuperPassword#456'})


async def test_refresh_rotation_rejects_replay(client, admin_creds):
    old = (await login(client, admin_creds))['refresh_token']
    client.cookies.clear()
    fresh = await client.post(f'{AUTH}/refresh', json={'refresh_token': old})
    assert fresh.status_code == 200
    client.cookies.clear()
    replay = await client.post(f'{AUTH}/refresh', json={'refresh_token': old})
    assert replay.status_code == 401
    assert (await client.post(f'{AUTH}/refresh', json={'refresh_token': fresh.json()['refresh_token']})).status_code == 200


async def test_logout_revokes_access_and_refresh(client, admin_creds):
    old = await login(client, admin_creds)
    assert (await client.post(f'{AUTH}/logout')).status_code == 200
    client.cookies.clear()
    assert (await client.get(f'{AUTH}/me', headers={'Authorization': f"Bearer {old['access_token']}"})).status_code == 401
    assert (await client.post(f'{AUTH}/refresh', json={'refresh_token': old['refresh_token']})).status_code == 401


async def test_password_mandatory_and_old_sessions_invalid(client, admin_creds):
    await database.get_db()['users'].update_one({'email': admin_creds['email']},
        {'$set': {'must_change_password': True}})
    old = await login(client, admin_creds)
    assert old['user']['must_change_password'] is True
    assert (await client.get('/api/v1/admin/users')).status_code == 403
    pw = await client.post(f'{AUTH}/change-password', json={
        'current_password': admin_creds['password'], 'new_password': 'NewSuperPassword#456'})
    assert pw.status_code == 200, pw.text
    client.cookies.clear()
    assert (await client.post(f'{AUTH}/refresh', json={'refresh_token': old['refresh_token']})).status_code == 401
    assert (await client.get(f'{AUTH}/me', headers={'Authorization': f"Bearer {old['access_token']}"})).status_code == 401
    new = await login(client, {**admin_creds, 'password': 'NewSuperPassword#456'})
    assert new['user']['must_change_password'] is False


async def test_users_crud_and_roles_catalog(client, admin_creds):
    await change_default_password(client, admin_creds)
    roles = await client.get('/api/v1/admin/roles')
    assert roles.status_code == 200 and len(roles.json()['permission_catalog']) == 32
    create_role = await client.post('/api/v1/admin/roles', json={
        'name': 'reviewer', 'priority': 3, 'permissions': ['poi:read', 'poi:approve']})
    assert create_role.status_code == 201, create_role.text
    created = await client.post('/api/v1/admin/users', json={
        'email': 'reviewer@test.vn', 'full_name': 'Reviewer', 'password': 'TemporaryPassword#12',
        'role': 'reviewer', 'is_active': True})
    assert created.status_code == 201, created.text
    uid = created.json()['id']
    assert 'password_hash' not in created.text
    listed = await client.get('/api/v1/admin/users', params={'q': 'reviewer@test.vn'})
    assert listed.json()['total'] == 1
    assert (await client.patch(f'/api/v1/admin/users/{uid}', json={'is_active': False})).status_code == 200
    assert (await client.delete('/api/v1/admin/roles/reviewer')).status_code == 409
    assert (await client.delete(f'/api/v1/admin/users/{uid}')).status_code == 200
    assert (await client.delete('/api/v1/admin/roles/reviewer')).status_code == 200
    assert await database.get_db()['audit_logs'].count_documents({'action': 'user.soft_delete'}) == 1


async def test_protected_admin_and_csrf(client, admin_creds):
    await change_default_password(client, admin_creds)
    accounts = (await client.get('/api/v1/admin/users')).json()['items']
    admin_user = next(u for u in accounts if u['role'] == 'super_admin')
    assert (await client.patch(f"/api/v1/admin/users/{admin_user['id']}", json={'is_active': False})).status_code == 403
    assert (await client.patch('/api/v1/admin/roles/super_admin', json={'permissions': []})).status_code == 403
    bad = await client.post(f'{AUTH}/logout', headers={'Origin': 'https://evil.invalid'})
    assert bad.status_code == 403


async def test_api_role_permission_effect_immediate(client, admin_creds):
    await change_default_password(client, admin_creds)
    await client.patch('/api/v1/admin/roles/admin', json={'permissions': ['poi:read']})
    result = await client.post('/api/v1/admin/users', json={
        'email': 'admin2@test.vn', 'full_name': 'Admin 2', 'password': 'TemporaryPassword#12', 'role': 'admin'})
    assert result.status_code == 201
    await login(client, {'email': 'admin2@test.vn', 'password': 'TemporaryPassword#12'})
    assert (await client.get('/api/v1/admin/users')).status_code == 403
    await database.get_db()['roles'].update_one({'name': 'admin'}, {'$push': {'permissions': 'user:read'}})
    # Password-change flag must be cleared to use admin routes.
    await client.post(f'{AUTH}/change-password', json={
        'current_password': 'TemporaryPassword#12', 'new_password': 'AnewSecurePassword#345'})
    await login(client, {'email': 'admin2@test.vn', 'password': 'AnewSecurePassword#345'})
    assert (await client.get('/api/v1/admin/users')).status_code == 200
