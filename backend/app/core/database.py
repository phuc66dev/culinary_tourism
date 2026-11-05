"""
Kết nối bất đồng bộ tới MongoDB (Motor) và Redis.
Phụ trách: Vũ (Task 3.1)
"""
import logging
from typing import Any
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

logger = logging.getLogger("quan4.database")

# References cho Motor client, Database và Redis
mongo_client: Any = None
db: Any = None
redis_client: Any = None


async def connect_db() -> None:
    """Khởi tạo AsyncIOMotorClient và tạo các indexes cốt lõi."""
    global mongo_client, db
    try:
        mongo_client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=3000)
        db = mongo_client[settings.DB_NAME]
        # Tạo index không gian địa lý 2dsphere cho POIs
        await db.pois.create_index([("location", "2dsphere")])
        # Tạo index cho Users
        await db.users.create_index([("email", 1)], unique=True, sparse=True)
        await db.users.create_index([("username", 1)], unique=True, sparse=True)
        await db.users.create_index([("device_id", 1)], sparse=True)
        # Tạo index cho Lịch sử nghe & OTP
        await db.listening_histories.create_index([("user_id", 1)])
        await db.listening_histories.create_index([("device_id", 1)])
        await db.email_verifications.create_index([("email", 1)])
        await db.password_resets.create_index([("email", 1)])
    except Exception as e:
        print(f"MongoDB connection notice: {e}")


async def close_db() -> None:
    """Đóng kết nối MongoDB và Redis khi ứng dụng tắt."""
    global mongo_client
    if mongo_client:
        mongo_client.close()


def get_db() -> Any:
    """Dependency cung cấp instance MongoDB database."""
    return db
