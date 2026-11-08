import binascii
import hashlib
import hmac
import os
import time
from typing import Dict, Optional
import jwt
from app.core.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash password bằng PBKDF2-HMAC-SHA256 (100,000 vòng)."""
    salt = os.urandom(16)
    salt_hex = binascii.hexlify(salt).decode()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return f"{salt_hex}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Đối chiếu mật khẩu đã hash."""
    try:
        salt_hex, hash_hex = stored.split("$")
    except Exception:
        return False
    salt = binascii.unhexlify(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return hmac.compare_digest(dk.hex(), hash_hex)


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    now = int(time.time())
    expires = now + (expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60
    payload = {
        "sub": subject,
        "type": "access",
        "exp": expires,
        "iat": now,
    }
    return jwt.encode(payload, settings.JWT_SECRET or settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str, expires_days: Optional[int] = None) -> str:
    now = int(time.time())
    expires = now + (expires_days or settings.REFRESH_TOKEN_EXPIRE_DAYS) * 24 * 3600
    payload = {
        "sub": subject,
        "type": "refresh",
        "exp": expires,
        "iat": now,
    }
    return jwt.encode(payload, settings.REFRESH_TOKEN_SECRET or settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, secret: Optional[str] = None) -> Dict:
    """Decode JWT token (ném ngoại lệ nếu hết hạn hoặc sai chữ ký)."""
    key = secret or settings.JWT_SECRET or settings.SECRET_KEY
    return jwt.decode(token, key, algorithms=[ALGORITHM])

