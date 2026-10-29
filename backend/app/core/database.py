import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

logger = logging.getLogger("quan4.database")

mongo_client: Any = None
db: Any = None
redis_client: Any = None  # Optional: None nếu Redis không khả dụng (ứng dụng vẫn chạy bình thường)


# ==========================================
# Danh sách collection của hệ thống (tài liệu hóa ở docs/DATABASE_SCHEMA.md)
# ==========================================
COLLECTIONS = {
    "POI": "poi",
    "POI_LOCALIZATIONS": "poi_localizations",
    "USERS": "users",
    "ROLES": "roles",
    "OWNER_REGISTRATIONS": "poi_owner_registrations",
    "POI_SUBMISSIONS": "poi_submissions",
    "MENU_ITEMS": "menu_items",
    "NOTIFICATIONS": "notifications",
    "AUDIO_TASKS": "audio_tasks",
    "AUDIT_LOGS": "audit_logs",
    "SYSTEM_META": "system_meta",
    "REFRESH_SESSIONS": "refresh_sessions",
}


async def connect_db() -> None:
    """Khởi tạo Motor + (tuỳ chọn) Redis, rồi tạo toàn bộ indexes cốt lõi."""
    global mongo_client, db, redis_client
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo_client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client[settings.DB_NAME]
    await mongo_client.admin.command("ping")  # Fail-fast nếu MongoDB chưa chạy
    logger.info("MongoDB connected: %s", settings.DB_NAME)
    # Multi-document transactions require an actual replica set (standalone MongoDB is not sufficient).
    hello = await mongo_client.admin.command("hello")
    if not hello.get("setName"):
        raise RuntimeError("MongoDB replica set chưa được khởi tạo. Chạy docker compose init và rs.initiate() (xem docs/CORE_AUTH_RBAC_COMPLETION.md).")

    # Redis là tuỳ chọn — dùng cho cache/rate-limit về sau, không làm sập backend nếu thiếu.
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        redis_client = client
        logger.info("Redis connected")
    except Exception as exc:  # noqa: BLE001
        redis_client = None
        logger.warning("Redis không khả dụng (%s) — chạy ở chế độ không cache.", exc)

    await ensure_indexes(db)


async def close_db() -> None:
    """Đóng kết nối MongoDB và Redis khi ứng dụng tắt."""
    global mongo_client, db, redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None
    if mongo_client is not None:
        mongo_client.close()
        mongo_client = None
    db = None


def get_db() -> Any:
    """Dependency cung cấp instance MongoDB database."""
    if db is None:
        raise RuntimeError("Database chưa được khởi tạo — connect_db() chưa chạy.")
    return db


async def ping_db() -> bool:
    """Dùng cho /health/ready."""
    try:
        await get_db().command("ping")
        return True
    except Exception:  # noqa: BLE001
        return False


async def ensure_indexes(database: Any) -> None:
    """Idempotent: chạy lại nhiều lần không lỗi. Gọi lúc startup và trong seed script."""
    # --- poi: index không gian cho $geoNear + lọc quản trị ---
    await database["poi"].create_index([("location", "2dsphere")], name="location_2dsphere")
    await database["poi"].create_index("slug", unique=True, sparse=True, name="slug_unique")
    await database["poi"].create_index([("is_active", 1), ("updated_at", -1)], name="active_updated")
    await database["poi"].create_index("ward", name="ward")
    await database["poi"].create_index("owner_id", sparse=True, name="owner_id")

    # --- poi_localizations: mỗi (poi, ngôn ngữ) đúng 1 bản ghi ---
    await database["poi_localizations"].create_index(
        [("poi_id", 1), ("lang", 1)], unique=True, name="poi_lang_unique"
    )

    # --- users / roles ---
    await database["users"].create_index("email", unique=True, name="email_unique")
    await database["users"].create_index("role", name="role")
    await database["roles"].create_index("name", unique=True, name="role_name_unique")
    await database["refresh_sessions"].create_index("expires_at", expireAfterSeconds=0, name="expires_ttl")
    await database["refresh_sessions"].create_index([("user_id", 1), ("revoked_at", 1)], name="user_revoked")

    # --- owner flow ---
    await database["poi_owner_registrations"].create_index(
        [("status", 1), ("created_at", -1)], name="status_created"
    )
    await database["poi_owner_registrations"].create_index("user_id", name="user_id")
    await database["poi_submissions"].create_index(
        [("status", 1), ("created_at", -1)], name="status_created"
    )
    await database["poi_submissions"].create_index("poi_id", name="poi_id")
    await database["menu_items"].create_index("poi_id", name="poi_id")
    await database["notifications"].create_index(
        [("user_id", 1), ("is_read", 1), ("created_at", -1)], name="user_read_created"
    )

    # --- audio_tasks / audit_logs ---
    await database["audio_tasks"].create_index(
        [("status", 1), ("updated_at", -1)], name="status_updated"
    )
    # MongoDB enforces one active task per POI across ALL backend instances.
    # If migrating existing duplicate tasks, resolve duplicates before starting.
    await database["audio_tasks"].create_index(
        "poi_id", unique=True, name="one_active_audio_task_per_poi",
        partialFilterExpression={"status": {"$in": ["queued", "running", "paused"]}},
    )
    await database["audit_logs"].create_index([("created_at", -1)], name="created_desc")
    await database["audit_logs"].create_index([("user_id", 1), ("created_at", -1)], name="user_created")
    await database["audit_logs"].create_index([("action", 1), ("created_at", -1)], name="action_created")
    await database["audit_logs"].create_index([("resource", 1), ("created_at", -1)], name="resource_created")
    logger.info("MongoDB indexes ensured")


@asynccontextmanager
async def mongo_transaction():
    """Start an actual MongoDB multi-document transaction; never silently downgrade to separate writes.

    Callers must pass `session=session` to every Mongo operation belonging to
    the transaction. MongoDB replica set / Atlas deployment is mandatory.
    """
    # Unit tests use in-memory mongomock and cannot exercise real Mongo transactions.
    # This bypass is test-only; production/development never silently downgrade.
    if settings.APP_ENV.lower() == "test" and mongo_client is None:
        yield None
        return
    if mongo_client is None:
        raise RuntimeError("MongoDB client chưa khởi tạo: không thể bắt đầu transaction")
    async with await mongo_client.start_session() as session:
        async with session.start_transaction():
            yield session
