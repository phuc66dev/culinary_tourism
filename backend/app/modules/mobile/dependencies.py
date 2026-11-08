from typing import Optional
from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.database import get_db
from app.modules.mobile.utils.security import decode_token

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[dict]:
    """Lấy user từ Bearer Header hoặc httpOnly Cookie (không bắt buộc đăng nhập)."""
    token = None
    if credentials:
        token = credentials.credentials
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        return None

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id:
            db = get_db()
            user = await db.users.find_one({"_id": user_id})
            return user
    except Exception:
        pass
    return None


async def get_current_user_required(
    current_user: Optional[dict] = Depends(get_current_user_optional),
) -> dict:
    """Bắt buộc người dùng phải đăng nhập hợp lệ."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Yêu cầu đăng nhập để thực hiện chức năng này")
    return current_user

