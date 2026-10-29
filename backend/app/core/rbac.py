"""
Động cơ Phân quyền Động (Dynamic RBAC) — 32 Permissions trên 9 Domains.
Phụ trách: Vũ (Task 3.3)
"""
from typing import Callable

from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user

# 9 Permission Domains & 32 Static Permissions theo PRD
PERMISSION_DOMAINS: dict[str, list[str]] = {
    "poi": ["read", "create", "update", "delete", "approve", "toggle"],
    "menu": ["read", "create", "update", "delete"],
    "user": ["read", "create", "update", "delete"],
    "role": ["read", "create", "update", "delete"],
    "analytics": ["view", "export", "view_own"],
    "audit": ["read", "manage"],
    "system": ["config", "logs", "backup"],
    "owner": ["register", "access", "submit_poi", "manage_own_poi"],
    "content": ["moderate", "publish"],
}

ALL_PERMISSIONS: list[str] = [
    f"{domain}:{action}"
    for domain, actions in PERMISSION_DOMAINS.items()
    for action in actions
]

# 4 Vai trò mặc định (Default Roles)
DEFAULT_ROLES: dict[str, dict] = {
    "super_admin": {
        "priority": 0,
        "permissions": ALL_PERMISSIONS,
    },
    "admin": {
        "priority": 1,
        "permissions": [
            p for p in ALL_PERMISSIONS if not p.startswith(("role:", "system:"))
        ],
    },
    "poi_owner": {
        "priority": 2,
        "permissions": [
            "owner:access",
            "owner:submit_poi",
            "owner:manage_own_poi",
            "menu:read",
            "menu:create",
            "menu:update",
            "menu:delete",
            "analytics:view_own",
        ],
    },
    "user": {
        "priority": 3,
        "permissions": ["poi:read", "menu:read", "owner:register"],
    },
}


def require_permission(permission: str) -> Callable:
    """
    Dependency Guard kiểm tra quyền trên từng Route.

        @router.post("/pois/{id}/approve")
        async def approve(user: dict = Depends(require_permission("poi:approve"))): ...

    - Chưa đăng nhập → 401. Đăng nhập nhưng thiếu quyền → 403.
    - Quyền được đọc từ collection `roles` mỗi request (Dynamic RBAC), không nhúng cứng trong JWT.
    - Trả về dict current_user nên route có thể dùng luôn (`user["id"]`, `user["role"]`...).
    """
    if permission not in ALL_PERMISSIONS:
        # Bắt lỗi gõ sai ngay lúc import module, không đợi tới lúc có request.
        raise ValueError(f"Permission không tồn tại: {permission!r}")

    async def _permission_guard(user: dict = Depends(get_current_user)) -> dict:
        if permission not in user["permissions"]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Bạn không có quyền thực hiện thao tác này ({permission})",
            )
        return user

    return _permission_guard
