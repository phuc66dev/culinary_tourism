"""
Kết nối bất đồng bộ tới MongoDB (Motor) và Redis.
Phụ trách: Vũ (Task 3.1)
"""
from typing import Any
from app.core.config import settings

# Skeleton references cho Motor client, Database và Redis
mongo_client: Any = None
db: Any = None
redis_client: Any = None


async def connect_db() -> None:
    """
    TODO (Vũ - Task 3.1):
    - Khởi tạo AsyncIOMotorClient(settings.MONGO_URI)
    - Gán db = mongo_client[settings.DB_NAME]
    - Kiểm tra kết nối Redis (nếu cấu hình)
    - Tạo các indexes cốt lõi (2dsphere cho POI, TTL cho rate limits)
    """
    pass


async def close_db() -> None:
    """Đóng kết nối MongoDB và Redis khi ứng dụng tắt."""
    pass


def get_db() -> Any:
    """Dependency cung cấp instance MongoDB database."""
    return db
