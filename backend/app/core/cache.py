import hashlib
import hmac
import json
import logging
from app.core import database
from app.core.config import settings

logger = logging.getLogger(__name__)


async def cache_get_json(key: str):
    redis = database.redis_client
    if redis is None:
        return None
    try:
        value = await redis.get(key)
        return json.loads(value) if value is not None else None
    except Exception:
        logger.warning("Redis cache GET failed", exc_info=True)
        return None


async def cache_set_json(key: str, value, ttl: int = 15):
    redis = database.redis_client
    if redis is None:
        return
    try:
        await redis.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=ttl)
    except Exception:
        logger.warning("Redis cache SET failed", exc_info=True)


def login_limit_key(email: str, ip: str | None) -> str:
    identity = f"{(ip or 'unknown').strip()}:{email.strip().casefold()}"
    digest = hmac.new(settings.JWT_SECRET.encode(), identity.encode(), hashlib.sha256).hexdigest()[:32]
    return f"auth:limit:{digest}"


async def login_attempt_allowed(email: str, ip: str | None, max_attempts: int = 12, window_seconds: int = 600) -> bool:
    redis = database.redis_client
    if redis is None:
        return True
    try:
        key = login_limit_key(email, ip)
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
        return count <= max_attempts
    except Exception:
        logger.warning("Redis rate limit unavailable", exc_info=True)
        return True


async def login_attempt_clear(email: str, ip: str | None):
    redis = database.redis_client
    if redis is None:
        return
    try:
        await redis.delete(login_limit_key(email, ip))
    except Exception:
        logger.warning("Redis rate limit reset failed", exc_info=True)
