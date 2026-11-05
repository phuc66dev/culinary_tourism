"""
Bảo mật, Xác thực Cookie httpOnly JWT, Mã hóa PII (Fernet) & Chống Path Traversal.
"""
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.database import get_db


# ==========================================
# 1. Cookie httpOnly JWT + Bearer Dual-Mode (Vũ - Task 3.2)
# ==========================================
ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
# Refresh cookie chỉ được gửi lên các endpoint auth → giảm bề mặt lộ token.
REFRESH_COOKIE_PATH = "/api/v1/admin/auth"

# Hiển thị nút "Authorize" (Bearer) trên Swagger; auto_error=False để cookie vẫn là ưu tiên.
bearer_scheme = HTTPBearer(auto_error=False, description="Chỉ dùng để test API. Trình duyệt dùng httpOnly Cookie.")


def hash_password(raw: str) -> str:
    raw_bytes = raw.encode("utf-8")
    if len(raw_bytes) > 72:  # giới hạn của bcrypt
        raise ValueError("Password tối đa 72 bytes")
    return bcrypt.hashpw(raw_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        raw_bytes = raw.encode("utf-8")
        if len(raw_bytes) > 72:
            return False
        return bcrypt.checkpw(raw_bytes, hashed.encode("utf-8"))
    except ValueError:
        return False


def _encode(payload: dict, token_type: str, secret: str, ttl: timedelta) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        **payload,
        "type": token_type,
        "iat": now,
        "exp": now + ttl,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(claims, secret, algorithm=settings.JWT_ALGORITHM)


def create_access_token(payload: dict) -> str:
    """JWT access_token (hạn 30 phút, HS256). `payload` tối thiểu: {"sub": user_id, "role": role}."""
    return _encode(payload, "access", settings.JWT_SECRET, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(payload: dict) -> str:
    """JWT refresh_token (hạn 7 ngày, HS256), ký bằng secret riêng."""
    return _encode(payload, "refresh", settings.REFRESH_TOKEN_SECRET, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: str) -> dict:
    """Giải mã + kiểm tra loại token. Ném 401 nếu hết hạn / sai chữ ký / sai loại."""
    secret = settings.JWT_SECRET if expected_type == "access" else settings.REFRESH_TOKEN_SECRET
    try:
        claims = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token đã hết hạn") from None
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token không hợp lệ") from None
    if claims.get("type") != expected_type or not claims.get("sub"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token không hợp lệ")
    return claims


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    common = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "domain": settings.COOKIE_DOMAIN,
    }
    response.set_cookie(
        ACCESS_COOKIE, access_token, max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/", **common
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=REFRESH_COOKIE_PATH,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/", domain=settings.COOKIE_DOMAIN)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, domain=settings.COOKIE_DOMAIN)


async def get_role_permissions(role_name: str) -> list[str]:
    """Dynamic RBAC: quyền của vai trò luôn đọc từ collection `roles` (admin sửa là có hiệu lực ngay)."""
    role = await get_db()["roles"].find_one({"name": role_name}, {"permissions": 1})
    return list(role["permissions"]) if role else []


async def load_user_context(user_id: str) -> dict | None:
    """Nạp user + permissions từ DB. Trả None nếu không tồn tại hoặc bị khóa."""
    try:
        oid = ObjectId(user_id)
    except (InvalidId, TypeError):
        return None
    user = await get_db()["users"].find_one({"_id": oid})
    if not user or not user.get("is_active", True):
        return None
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "full_name": user.get("full_name"),
        "role": user["role"],
        "permissions": await get_role_permissions(user["role"]),
        "is_poi_owner_verified": bool(user.get("is_poi_owner_verified", False)),
        "must_change_password": bool(user.get("must_change_password", False)),
    }


async def get_current_user(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """
    Dual-mode Authentication:
    1. Ưu tiên đọc `access_token` từ httpOnly Cookie (trình duyệt).
    2. Fallback đọc từ Header `Authorization: Bearer <token>` (Swagger / API test).

    Trả về dict: id, email, full_name, role, permissions, is_poi_owner_verified, must_change_password.
    """
    token = request.cookies.get(ACCESS_COOKIE) or (bearer.credentials if bearer else None)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chưa đăng nhập")
    claims = decode_token(token, "access")
    user = await load_user_context(claims["sub"])
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tài khoản không tồn tại hoặc đã bị khóa")
    sid = claims.get("sid")
    if not isinstance(sid, str) or len(sid) != 64:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Phiên đăng nhập đã hết hiệu lực")
    session = await get_db()["refresh_sessions"].find_one({
        "_id": sid, "user_id": user["id"], "revoked_at": None,
        "expires_at": {"$gt": datetime.now(timezone.utc)},
    }, {"_id": 1})
    if not session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Phiên đăng nhập đã bị đăng xuất")
    actual = await get_db()["users"].find_one({"_id": ObjectId(user["id"])}, {"token_version": 1})
    if not actual or claims.get("sv", 0) != actual.get("token_version", 0):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Phiên đăng nhập đã bị thu hồi")
    if user["must_change_password"] and request.url.path not in (
        "/api/v1/admin/auth/me", "/api/v1/admin/auth/change-password", "/api/v1/admin/auth/logout",
    ):
        raise HTTPException(403, "Bạn phải đổi mật khẩu trước khi tiếp tục")
    return user


# ==========================================
# 2. Mã hóa đối xứng PII / CCCD (Phúc - Task 2.2)
# ==========================================
def encrypt_pii(raw_cccd: str) -> str:
    """
    TODO (Phúc - Task 2.2):
    Mã hóa chuỗi CCCD bằng Fernet và trả về định dạng `v1:<encrypted_string>`.
    """
    raise NotImplementedError("TODO: Implement encrypt_pii")


def decrypt_pii(encrypted_value: str) -> str:
    """
    TODO (Phúc - Task 2.2 / Vũ - Task 3.5):
    Giải mã chuỗi `v1:<encrypted_string>` để Admin đối chiếu khi duyệt đơn.
    """
    raise NotImplementedError("TODO: Implement decrypt_pii")


# ==========================================
# 3. Static Asset Path Traversal Guard (Task 3.11)
# ==========================================
# Backward-compatible import; the implementation lives in a side-effect-free
# module so both security.py and StaticFiles use exactly the same validation.
from app.core.path_security import resolve_safe_path  # noqa: E402,F401
