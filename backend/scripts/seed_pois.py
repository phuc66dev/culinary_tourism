"""
Script khởi tạo dữ liệu mẫu (5 quán ăn Quận 4) và đánh chỉ mục không gian (2dsphere).
Phụ trách: Vũ (Task 3.1 - Sprint 1)

Cách chạy:
    cd backend
    python -m scripts.seed_pois
"""
import asyncio
import json
from pathlib import Path


async def seed_database() -> None:
    """
    TODO (Vũ - Task 3.1):
    1. Kết nối MongoDB qua Motor (`app.core.database`).
    2. Tạo 2dsphere index cho `POI.location`:
       await db["POI"].create_index([("location", "2dsphere")])
    3. Tạo compound index cho `poi_localizations`:
       await db["poi_localizations"].create_index([("poi_id", 1), ("lang", 1)], unique=True)
    4. Đọc file `../data/seed/sample_pois_quan4.json` và upsert 5 quán mẫu.
    5. Khởi tạo 4 vai trò mặc định (`ensure_roles`) và tài khoản `super_admin` (`ensure_super_admin`).
    """
    seed_file = Path(__file__).resolve().parents[2] / "data" / "seed" / "sample_pois_quan4.json"
    print(f"[Seed Skeleton] Đọc dữ liệu mẫu từ: {seed_file}")
    if seed_file.exists():
        items = json.loads(seed_file.read_text(encoding="utf-8"))
        print(f"[Seed Skeleton] Tìm thấy {len(items)} địa điểm POI mẫu Quận 4 sẵn sàng nạp vào MongoDB.")


if __name__ == "__main__":
    asyncio.run(seed_database())
