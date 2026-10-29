
import hashlib
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, decode_token


def _now():
    return datetime.now(timezone.utc)


def _digest(jti: str) -> str:
    return hashlib.sha256(jti.encode()).hexdigest()


def _claims(user: dict) -> dict:
    return {"sub": str(user["_id"]), "role": user["role"], "sv": user.get("token_version", 0)}


async def issue_tokens(user: dict, *, session=None) -> tuple[str, str]:
    claims = _claims(user)
    refresh = create_refresh_token(claims)
    decoded = decode_token(refresh, "refresh")
    access = create_access_token({**claims, "sid": _digest(decoded["jti"])})
    await get_db()["refresh_sessions"].insert_one({
        "_id": _digest(decoded["jti"]),
        "user_id": str(user["_id"]),
        "expires_at": datetime.fromtimestamp(decoded["exp"], tz=timezone.utc),
        "created_at": _now(), "revoked_at": None,
    }, session=session)
    return access, refresh


async def rotate_tokens(raw_refresh: str, user: dict, *, session=None) -> tuple[str, str]:
    old = decode_token(raw_refresh, "refresh")
    if old["sub"] != str(user["_id"]) or old.get("sv", 0) != user.get("token_version", 0):
        raise HTTPException(401, "Phiên đăng nhập đã bị thay đổi")
    new_refresh = create_refresh_token(_claims(user))
    new = decode_token(new_refresh, "refresh")
    access = create_access_token({**_claims(user), "sid": _digest(new["jti"])})
    db = get_db()
    # Insert before consuming the old token; if old has already been used,
    # remove the orphan immediately and reject replay without issuing cookies.
    new_id = _digest(new["jti"])
    await db["refresh_sessions"].insert_one({
        "_id": new_id, "user_id": str(user["_id"]),
        "expires_at": datetime.fromtimestamp(new["exp"], tz=timezone.utc),
        "created_at": _now(), "revoked_at": None,
    }, session=session)
    result = await db["refresh_sessions"].update_one(
        {"_id": _digest(old.get("jti", "")), "user_id": str(user["_id"]),
         "revoked_at": None, "expires_at": {"$gt": _now()}},
        {"$set": {"revoked_at": _now(), "rotated_to": new_id}},
        session=session,
    )
    if result.modified_count != 1:
        await db["refresh_sessions"].delete_one({"_id": new_id}, session=session)
        raise HTTPException(401, "Refresh token không còn hiệu lực (đã dùng hoặc đăng xuất)")
    return access, new_refresh


async def revoke_refresh(raw_refresh: str | None, *, session=None) -> None:
    if not raw_refresh:
        return
    try:
        claims = decode_token(raw_refresh, "refresh")
    except HTTPException:
        return
    await get_db()["refresh_sessions"].update_one(
        {"_id": _digest(claims.get("jti", "")), "user_id": claims["sub"]},
        {"$set": {"revoked_at": _now()}}, session=session,
    )


async def revoke_all_sessions(user_id: str, *, session=None) -> None:
    await get_db()["refresh_sessions"].update_many(
        {"user_id": user_id, "revoked_at": None},
        {"$set": {"revoked_at": _now()}}, session=session,
    )


async def revoke_access_session(raw_access: str | None, *, session=None) -> None:
    """Allow Swagger/Bearer-only logout to revoke the matching session too."""
    if not raw_access:
        return
    try:
        claims = decode_token(raw_access, "access")
    except HTTPException:
        return
    sid = claims.get("sid")
    if isinstance(sid, str) and len(sid) == 64:
        await get_db()["refresh_sessions"].update_one(
            {"_id": sid, "user_id": claims["sub"]}, {"$set": {"revoked_at": _now()}}, session=session)
