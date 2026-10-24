"""
Động cơ Phân quyền Động (Dynamic RBAC) — 32 Permissions trên 9 Domains.
Phụ trách: Vũ (Task 3.3)
"""
from typing import Callable

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
    Ví dụ: Depends(require_permission("poi:approve"))
    """
    async def _permission_guard() -> None:
        # TODO (Vũ - Task 3.3): Kiểm tra permission trong JWT payload của current_user
        pass

    return _permission_guard
