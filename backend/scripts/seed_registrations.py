"""
Tạo hồ sơ đăng ký chủ quán MẪU (CCCD đã mã hoá Fernet `v1:`) để demo màn hình duyệt đơn (Task 3.5)
khi form đăng ký của Phúc chưa nối xong. Chỉ chạy ở môi trường không phải production.

    python -m scripts.seed_registrations            # idempotent theo email
    python -m scripts.seed_registrations --reset    # xoá hồ sơ + user demo rồi tạo lại
"""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet

from app.core import database
from app.core.config import settings
from app.core.security import hash_password

DEMO = [
    ("chu.quan.a@demo.vn", "Nguyễn Văn An", "0901000001", "Ốc Tô Vĩnh Khánh", "120 Vĩnh Khánh, Phường 10, Quận 4", "079201001234", "/static/images/poi/demo-storefront.svg"),
    ("chu.quan.b@demo.vn", "Trần Thị Bình", "0901000002", "Bún Mắm Cô Bình", "45 Hoàng Diệu, Phường 9, Quận 4", "079201005678", "/static/images/poi/demo-storefront.svg"),
    ("chu.quan.c@demo.vn", "Lê Minh Cường", "0901000003", "Chè Khúc Bạch Cường", "9 Tôn Đản, Phường 13, Quận 4", "079201009012", None),
]


async def main(reset: bool) -> None:
    if settings.is_production:
        raise SystemExit("Từ chối chạy seed demo ở production.")
    if not settings.FERNET_KEY:
        raise SystemExit("Thiếu FERNET_KEY trong .env — không thể mã hoá CCCD mẫu.")
    await database.connect_db()
    db = database.get_db()
    try:
        emails = [d[0] for d in DEMO]
        if reset:
            users = [u["_id"] async for u in db["users"].find({"email": {"$in": emails}}, {"_id": 1})]
            await db["poi_owner_registrations"].delete_many({"user_id": {"$in": users}})
            await db["users"].delete_many({"_id": {"$in": users}})
        fernet = Fernet(settings.FERNET_KEY.encode())
        now = datetime.now(timezone.utc)
        created = 0
        for i, (email, name, phone, poi_name, address, cccd, image) in enumerate(DEMO):
            user = await db["users"].find_one({"email": email})
            if not user:
                res = await db["users"].insert_one({
                    "email": email, "password_hash": hash_password("Demo@12345"), "full_name": name, "phone": phone,
                    "role": "poi_owner", "is_active": True, "is_poi_owner_verified": False,
                    "must_change_password": False, "created_at": now, "updated_at": now,
                })
                user = {"_id": res.inserted_id}
            if await db["poi_owner_registrations"].find_one({"user_id": user["_id"]}):
                continue
            await db["poi_owner_registrations"].insert_one({
                "user_id": user["_id"], "full_name": name, "phone": phone, "poi_name": poi_name,
                "poi_address": address, "storefront_image_url": image,
                "cccd_encrypted": "v1:" + fernet.encrypt(cccd.encode()).decode(),
                "status": "pending", "admin_note": None, "created_at": now - timedelta(hours=i * 5),
            })
            created += 1
        print(f"[Seed] Hồ sơ đăng ký mẫu: +{created} (pending). Mật khẩu chủ quán demo: Demo@12345")
    finally:
        await database.close_db()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    asyncio.run(main(parser.parse_args().reset))
