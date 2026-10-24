"""
AdminService — Xử lý Auth, Seeding Roles/SuperAdmin, Kiểm duyệt Owner/Submission & Audit Logs.
Phụ trách: Vũ (Task 3.2 - 3.6, Task 3.10)
"""


class AdminService:
    async def ensure_roles(self) -> None:
        """TODO (Vũ - Task 3.3): Seed 4 default roles vào collection `roles`."""
        pass

    async def ensure_super_admin(self) -> None:
        """TODO (Vũ - Task 3.3): Tạo tài khoản super_admin mặc định nếu chưa tồn tại."""
        pass

    async def log_audit(self, user_id: str, action: str, resource: str, ip: str | None = None) -> None:
        """TODO (Vũ - Task 3.10): Ghi nhận nhật ký thao tác nhạy cảm vào collection `audit_logs`."""
        pass


admin_service = AdminService()
