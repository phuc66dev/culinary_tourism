"""Fixtures dùng DB giả lập trong bộ nhớ (mongomock-motor) — không cần MongoDB thật."""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.core import database
from app.core.config import settings
from app.main import app
from app.modules.admin.service import admin_service


@pytest_asyncio.fixture
async def client(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "test")
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)  # httpx test client chạy http
    monkeypatch.setattr(settings, "SUPERADMIN_BOOTSTRAP_MODE", "auto")
    monkeypatch.setattr(database, "db", AsyncMongoMockClient()["quan4_test"])
    await admin_service.ensure_roles()
    await admin_service.ensure_super_admin()
    # The pre-existing admin integration tests operate on a bootstrap account.
    # Clear the onboarding flag only in the mock fixture; the new test below
    # explicitly verifies that a real bootstrap account is forced to change it.
    await database.get_db()["users"].update_one(
        {"email": settings.SUPERADMIN_EMAIL.lower()},
        {"$set": {"must_change_password": False}},
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def admin_creds():
    return {"email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD}
