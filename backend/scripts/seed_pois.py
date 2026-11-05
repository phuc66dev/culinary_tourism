"""
Script khởi tạo dữ liệu mẫu (5 quán ăn Quận 4), roles, super_admin và toàn bộ indexes.
Phụ trách: Vũ (Task 3.1 - Sprint 1)

Cách chạy (từ thư mục backend/, MongoDB phải đang chạy):
    python -m scripts.seed_pois              # idempotent: chạy lại không ghi đè dữ liệu đã có
    python -m scripts.seed_pois --reset      # xóa poi + poi_localizations rồi seed lại từ đầu
    python -m scripts.seed_pois --no-demo-users

Lưu ý: seed POI mặc định ở trạng thái chưa công khai (is_active=false)
để tuân thủ Activation Gate; tạo audio EN xong thì bật trong POI Master.

Tài khoản demo (chỉ tạo khi APP_ENV != production), mật khẩu = DEMO_PASSWORD (mặc định Demo@12345):
    admin.demo@quan4culinary.vn   role=admin
    owner.demo@quan4culinary.vn   role=poi_owner (đã xác minh, sở hữu "Nem Nướng Nia")
"""
import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.core import database
from app.core.config import settings
from app.core.database import ensure_indexes
from app.core.security import hash_password
from app.modules.admin.service import admin_service
from app.modules.audio.source_version import source_fingerprint

SEED_FILE = Path(__file__).resolve().parents[2] / "data" / "seed" / "sample_pois_quan4.json"
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "Demo@12345")
OWNER_DEMO_POI_SLUG = "nem-nuong-nia"


async def seed_pois(db, items: list[dict]) -> tuple[int, int]:
    """Insert-if-missing theo `slug`. Trả về (số POI mới, số localization mới)."""
    now = datetime.now(timezone.utc)
    new_pois = new_locs = 0
    for item in items:
        localizations = item.pop("localizations", {})
        slug = item["slug"]
        # Gắn fingerprint để AudioTaskManager dùng lại bản dịch EN có sẵn
        # thay vì gọi lại Google Translate khi vừa seed dữ liệu mẫu.
        fingerprint = source_fingerprint(item.get("name", ""), item.get("original_description", ""))
        res = await db["poi"].update_one(
            {"slug": slug},
            {"$setOnInsert": {**{k: v for k, v in item.items() if k != "slug"}, "owner_id": None, "created_at": now, "updated_at": now}},
            upsert=True,
        )
        new_pois += 1 if res.upserted_id else 0
        poi = await db["poi"].find_one({"slug": slug}, {"_id": 1})
        for lang, loc in localizations.items():
            r = await db["poi_localizations"].update_one(
                {"poi_id": poi["_id"], "lang": lang},
                {
                    "$setOnInsert": {
                        "title": loc["title"],
                        "description": loc["description"],
                        "source_hash": fingerprint,
                        "translation_origin": "manual" if lang != "vi" else "source",
                        "audio_url": None,  # audio sẽ do AudioTaskManager (Sprint 3) sinh ra
                        "audio_duration_seconds": None,
                        "audio_status": "pending",
                        "is_fallback": False,
                        "created_at": now,
                        "updated_at": now,
                    }
                },
                upsert=True,
            )
            new_locs += 1 if r.upserted_id else 0
    return new_pois, new_locs


async def seed_demo_users(db) -> int:
    """Tài khoản demo cho Phúc (đăng nhập Owner) & Bảo. Chỉ chạy ở môi trường không phải production."""
    now = datetime.now(timezone.utc)
    pw = hash_password(DEMO_PASSWORD)
    created = 0
    for email, name, role, verified in [
        ("admin.demo@quan4culinary.vn", "Admin Demo", "admin", False),
        ("owner.demo@quan4culinary.vn", "Chủ Quán Demo", "poi_owner", True),
    ]:
        res = await db["users"].update_one(
            {"email": email},
            {
                "$setOnInsert": {
                    "email": email,
                    "password_hash": pw,
                    "full_name": name,
                    "phone": None,
                    "role": role,
                    "is_active": True,
                    "is_poi_owner_verified": verified,
                    "must_change_password": False,
                    "created_at": now,
                    "updated_at": now,
                }
            },
            upsert=True,
        )
        created += 1 if res.upserted_id else 0
    owner = await db["users"].find_one({"email": "owner.demo@quan4culinary.vn"}, {"_id": 1})
    await db["poi"].update_one(
        {"slug": OWNER_DEMO_POI_SLUG, "owner_id": None}, {"$set": {"owner_id": owner["_id"]}}
    )
    return created


async def seed_database(reset: bool = False, demo_users: bool = True) -> None:
    await database.connect_db()
    db = database.get_db()
    try:
        if reset:
            await db["poi"].delete_many({})
            await db["poi_localizations"].delete_many({})
            print("[Seed] Đã xóa poi & poi_localizations (--reset).")

        await ensure_indexes(db)  # 2dsphere(poi.location), unique(poi_id, lang), ...
        await admin_service.ensure_roles()
        await admin_service.ensure_super_admin()

        items = json.loads(SEED_FILE.read_text(encoding="utf-8"))
        new_pois, new_locs = await seed_pois(db, items)
        await db["system_meta"].update_one(
            {"_id": "dataset"},
            {"$setOnInsert": {"version": 1, "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
        print(f"[Seed] POI: +{new_pois} mới / {len(items)} quán mẫu | Localizations: +{new_locs} mới")

        if demo_users and not settings.is_production:
            n = await seed_demo_users(db)
            print(f"[Seed] Demo users: +{n} mới (mật khẩu: {DEMO_PASSWORD})")

        print(f"[Seed] Super admin: {settings.SUPERADMIN_EMAIL}")
        print("[Seed] Hoàn tất.")
    finally:
        await database.close_db()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed dữ liệu mẫu Quận 4")
    parser.add_argument("--reset", action="store_true", help="Xóa POI + localizations trước khi seed")
    parser.add_argument("--no-demo-users", action="store_true", help="Không tạo tài khoản demo")
    args = parser.parse_args()
    asyncio.run(seed_database(reset=args.reset, demo_users=not args.no_demo_users))
