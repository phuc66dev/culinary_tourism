"""
Bảo mật, Xác thực Cookie httpOnly JWT, Mã hóa PII (Fernet) & Chống Path Traversal.
Phụ trách: Vũ (Task 3.2, Task 3.11) & Phúc (Task 2.2)
"""
from pathlib import Path
from fastapi import HTTPException, Request, status


# ==========================================
# 1. Cookie httpOnly JWT + Bearer Dual-Mode (Vũ - Task 3.2)
# ==========================================
def create_access_token(payload: dict) -> str:
    """TODO (Vũ - Task 3.2): Sinh JWT access_token (hạn 30 phút, HS256)."""
    raise NotImplementedError("TODO: Implement create_access_token")


def create_refresh_token(payload: dict) -> str:
    """TODO (Vũ - Task 3.2): Sinh JWT refresh_token (hạn 7 ngày, HS256)."""
    raise NotImplementedError("TODO: Implement create_refresh_token")


async def get_current_user(request: Request) -> dict:
    """
    TODO (Vũ - Task 3.2):
    Dual-mode Authentication:
    1. Ưu tiên đọc `access_token` từ httpOnly Cookie.
    2. Fallback đọc từ Header `Authorization: Bearer <token>`.
    """
    raise NotImplementedError("TODO: Implement get_current_user")


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
# 3. Static Asset Path Traversal Guard (Vũ - Task 3.11)
# ==========================================
def resolve_safe_path(base_dir: str | Path, requested_path: str) -> Path:
    """
    Kiểm tra đường dẫn tệp tĩnh an toàn, chặn tấn công Path Traversal (`../../etc/passwd`).
    """
    base = Path(base_dir).resolve()
    target = (base / requested_path.lstrip("/\\")).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid path: Path traversal detected.",
        )
    return target
