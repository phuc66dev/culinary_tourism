import asyncio
import logging
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from app.core.config import settings
from app.core.database import get_db
from app.core.rbac import ALL_PERMISSIONS, DEFAULT_ROLES
from app.core.security import hash_password, verify_password

logger = logging.getLogger("quan4.admin")

# Hash giả để login "email không tồn tại" tốn thời gian tương đương "sai mật khẩu" (chống dò email).
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AdminService:
    # ------------------------------------------------------------------
    # Bootstrap (Task 3.3)
    # ------------------------------------------------------------------
    async def ensure_roles(self) -> None:
        """
        Seed 4 default roles vào collection `roles` (idempotent).
        - Role chưa có  → tạo mới với quyền mặc định.
        - Role đã có    → GIỮ NGUYÊN quyền (admin có thể đã chỉnh qua Dynamic RBAC).
        - `super_admin` → luôn được đồng bộ đủ ALL_PERMISSIONS để quyền mới tự có hiệu lực.
        """
        roles = get_db()["roles"]
        now = _now()
        for name, spec in DEFAULT_ROLES.items():
            await roles.update_one(
                {"name": name},
                {
                    "$setOnInsert": {
                        "name": name,
                        "priority": spec["priority"],
                        "permissions": list(spec["permissions"]),
                        "is_system": True,
                        "created_at": now,
                    },
                    "$set": {"updated_at": now},
                },
                upsert=True,
            )
        await roles.update_one({"name": "super_admin"}, {"$set": {"permissions": list(ALL_PERMISSIONS)}})
        logger.info("Roles ensured: %s", ", ".join(DEFAULT_ROLES))

    async def ensure_super_admin(self) -> None:
        """Tạo tài khoản super_admin mặc định nếu chưa tồn tại (theo SUPERADMIN_BOOTSTRAP_MODE)."""
        if settings.SUPERADMIN_BOOTSTRAP_MODE.lower() != "auto":
            logger.info("Bỏ qua bootstrap super_admin (mode=%s)", settings.SUPERADMIN_BOOTSTRAP_MODE)
            return
        users = get_db()["users"]
        email = settings.SUPERADMIN_EMAIL.lower()
        if await users.find_one({"email": email}, {"_id": 1}):
            return
        now = _now()
        await users.insert_one(
            {
                "email": email,
                "password_hash": await asyncio.to_thread(hash_password, settings.SUPERADMIN_PASSWORD),
                "full_name": "Super Admin",
                "phone": None,
                "role": "super_admin",
                "is_active": True,
                "is_poi_owner_verified": False,
                "must_change_password": True,
                "created_at": now,
                "updated_at": now,
            }
        )
        logger.warning("Đã tạo super_admin %s — hãy đổi mật khẩu sau lần đăng nhập đầu.", email)

    # ------------------------------------------------------------------
    # Auth (Task 3.2)
    # ------------------------------------------------------------------
    async def authenticate(self, email: str, password: str) -> dict | None:
        """Trả về user document nếu đúng email/mật khẩu và tài khoản đang hoạt động, ngược lại None."""
        user = await get_db()["users"].find_one({"email": email.strip().lower()})
        hashed = user["password_hash"] if user else _DUMMY_HASH
        ok = await asyncio.to_thread(verify_password, password, hashed)
        if not user or not ok or not user.get("is_active", True):
            return None
        return user

    async def get_user_by_id(self, user_id: str) -> dict | None:
        try:
            return await get_db()["users"].find_one({"_id": ObjectId(user_id)})
        except (InvalidId, TypeError):
            return None

    # ------------------------------------------------------------------
    # Audit (Task 3.10)
    # ------------------------------------------------------------------
    async def log_audit(
        self,
        user_id: str | None,
        action: str,
        resource: str,
        ip: str | None = None,
        details: dict | None = None,
        *,
        strict: bool = True,
        session=None,
    ) -> None:
        """Append an audit event. `strict` blocks sensitive disclosure on DB failure.

        Mutation call sites record completion after their DB writes. A logging
        failure is reported in server logs; standalone MongoDB cannot make
        business writes + audit inserts atomic without multi-document transactions.
        """
        from app.modules.admin.audit import write_audit_event
        try:
            await write_audit_event(user_id, action, resource, ip, details, session=session)
        except Exception:
            logger.exception("Audit insert failed: %s %s", action, resource)
            if strict:
                from fastapi import HTTPException
                raise HTTPException(503, "Cannot persist security audit event") from None


admin_service = AdminService()
