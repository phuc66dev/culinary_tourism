import random
import time
import uuid
from typing import Optional, Tuple
from fastapi import HTTPException
from app.core.database import get_db
from app.modules.mobile.schemas import (
    ChangePasswordRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
)
from app.modules.mobile.utils.email_util import send_email
from app.modules.mobile.utils.i18n import t
from app.modules.mobile.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from app.core.config import settings


class MobileAuthService:
    @property
    def db(self):
        return get_db()

    async def authenticate_user(self, email_or_username: str, password: str, locale: str = "vi") -> dict:
        user = await self.db.users.find_one({
            "$or": [{"email": email_or_username}, {"username": email_or_username}]
        })
        if not user or not user.get("password_hash"):
            raise HTTPException(status_code=400, detail=t("invalid_credentials", locale))

        if not verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=400, detail=t("invalid_credentials", locale))

        user_id = str(user["_id"])
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        return {"accessToken": access_token, "refreshToken": refresh_token}

    async def register_request(self, req: RegisterRequest, locale: str = "vi") -> str:
        # Kiểm tra trùng email
        existing_email = await self.db.users.find_one({"email": req.email})
        if existing_email:
            raise HTTPException(status_code=400, detail=t("email_exists", locale))

        # Kiểm tra trùng username nếu có
        if req.username:
            existing_user = await self.db.users.find_one({"username": req.username})
            if existing_user:
                raise HTTPException(status_code=400, detail=t("username_exists", locale))

        otp = f"{random.randint(100000, 999999)}"
        expires_at = int(time.time()) + 15 * 60  # 15 phút
        hashed_pwd = hash_password(req.password)

        await self.db.email_verifications.update_one(
            {"email": req.email},
            {
                "$set": {
                    "username": req.username,
                    "password_hash": hashed_pwd,
                    "full_name": req.full_name,
                    "otp_code": otp,
                    "expires_at": expires_at,
                    "attempts": 0,
                    "updated_at": int(time.time()),
                }
            },
            upsert=True,
        )

        # Gửi OTP qua email
        try:
            subject = t("otp_subject", locale)
            body = t("otp_body", locale, otp=otp, minutes=15)
            await send_email(subject, req.email, body)
        except Exception as e:
            # Nếu chưa cấu hình SMTP, in OTP ra console để dev test
            print(f"[MobileAuth] DEV MODE - OTP for {req.email}: {otp} (Error: {e})")

        return t("otp_sent", locale)

    async def verify_registration(self, email: str, otp: str, locale: str = "vi") -> dict:
        record = await self.db.email_verifications.find_one({"email": email})
        if not record:
            raise HTTPException(status_code=400, detail=t("no_pending", locale))

        if int(time.time()) > record.get("expires_at", 0):
            raise HTTPException(status_code=400, detail=t("otp_expired", locale))

        if record.get("otp_code") != otp.strip():
            await self.db.email_verifications.update_one(
                {"email": email}, {"$inc": {"attempts": 1}}
            )
            raise HTTPException(status_code=400, detail=t("invalid_otp", locale))

        # Tạo user mới trong Mongo
        user_id = str(uuid.uuid4())
        user_doc = {
            "_id": user_id,
            "email": record["email"],
            "username": record.get("username") or record["email"].split("@")[0],
            "password_hash": record["password_hash"],
            "full_name": record.get("full_name") or "",
            "role": "user",
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        await self.db.users.insert_one(user_doc)
        await self.db.email_verifications.delete_one({"email": email})

        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        return {"accessToken": access_token, "refreshToken": refresh_token}

    async def login_or_create_by_device(self, device_id: str) -> dict:
        user = await self.db.users.find_one({"device_id": device_id})
        if not user:
            user_id = str(uuid.uuid4())
            short_id = device_id[:8] if len(device_id) >= 8 else device_id
            user_doc = {
                "_id": user_id,
                "device_id": device_id,
                "username": f"guest_{short_id}",
                "full_name": f"Guest {short_id}",
                "role": "user",
                "created_at": int(time.time()),
            }
            await self.db.users.insert_one(user_doc)
        else:
            user_id = str(user["_id"])

        return {
            "accessToken": create_access_token(user_id),
            "refreshToken": create_refresh_token(user_id),
        }

    async def login_with_google(self, token: str, locale: str = "vi") -> dict:
        audience = (
            settings.GOOGLE_CLIENT_ID.strip()
            if getattr(settings, "GOOGLE_CLIENT_ID", None) and settings.GOOGLE_CLIENT_ID.strip()
            else None
        )
        if audience and "," in audience:
            audience = [aud.strip() for aud in audience.split(",") if aud.strip()]

        try:
            idinfo = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), audience=audience
            )
        except (ValueError, GoogleAuthError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid Google token: {str(e)}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Google authentication failed: {str(e)}",
            )

        email = idinfo.get("email")
        if not email:
            raise HTTPException(
                status_code=400,
                detail="Google token does not contain an email address",
            )

        name = idinfo.get("name") or idinfo.get("given_name") or email.split("@")[0]
        picture = idinfo.get("picture")
        google_id = idinfo.get("sub")

        # Tìm tài khoản theo email
        user = await self.db.users.find_one({"email": email})
        if not user:
            base_username = email.split("@")[0]
            username = base_username
            existing_user = await self.db.users.find_one({"username": username})
            if existing_user:
                username = f"{base_username}_{uuid.uuid4().hex[:6]}"

            user_id = str(uuid.uuid4())
            user_doc = {
                "_id": user_id,
                "email": email,
                "username": username,
                "full_name": name,
                "avatar_url": picture,
                "google_id": google_id,
                "role": "user",
                "password_hash": None,
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }
            await self.db.users.insert_one(user_doc)
        else:
            user_id = str(user["_id"])
            updates = {"updated_at": int(time.time())}
            if not user.get("google_id") and google_id:
                updates["google_id"] = google_id
            if not user.get("avatar_url") and picture:
                updates["avatar_url"] = picture
            if not user.get("full_name") and name:
                updates["full_name"] = name
            if len(updates) > 1:
                await self.db.users.update_one({"_id": user["_id"]}, {"$set": updates})

        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        return {"accessToken": access_token, "refreshToken": refresh_token}

    async def forgot_password(self, email: str, locale: str = "vi") -> str:
        user = await self.db.users.find_one({"email": email})
        if not user:
            return t("reset_sent", locale)

        otp = f"{random.randint(100000, 999999)}"
        expires_at = int(time.time()) + 15 * 60

        await self.db.password_resets.update_one(
            {"email": email},
            {
                "$set": {
                    "otp_code": otp,
                    "expires_at": expires_at,
                    "used": False,
                    "updated_at": int(time.time()),
                }
            },
            upsert=True,
        )

        try:
            subject = t("reset_subject", locale)
            body = t("reset_body", locale, otp=otp, minutes=15)
            await send_email(subject, email, body)
        except Exception as e:
            print(f"[MobileAuth] DEV MODE - Reset OTP for {email}: {otp} (Error: {e})")

        return t("reset_sent", locale)

    async def reset_password(self, req: ResetPasswordRequest, locale: str = "vi") -> str:
        record = await self.db.password_resets.find_one({"email": req.email, "used": False})
        if not record:
            raise HTTPException(status_code=400, detail=t("no_pending", locale))

        if int(time.time()) > record.get("expires_at", 0):
            raise HTTPException(status_code=400, detail=t("otp_expired", locale))

        if record.get("otp_code") != req.otp.strip():
            raise HTTPException(status_code=400, detail=t("invalid_otp", locale))

        new_hash = hash_password(req.new_password)
        await self.db.users.update_one(
            {"email": req.email},
            {"$set": {"password_hash": new_hash, "updated_at": int(time.time())}},
        )
        await self.db.password_resets.update_one({"email": req.email}, {"$set": {"used": True}})
        return t("change_password_success", locale)

    async def change_password(self, user_id: str, req: ChangePasswordRequest, locale: str = "vi") -> str:
        user = await self.db.users.find_one({"_id": user_id})
        if not user or not user.get("password_hash"):
            raise HTTPException(status_code=400, detail=t("user_not_found", locale))

        if not verify_password(req.current_password, user["password_hash"]):
            raise HTTPException(status_code=400, detail=t("invalid_credentials", locale))

        new_hash = hash_password(req.new_password)
        await self.db.users.update_one(
            {"_id": user_id},
            {"$set": {"password_hash": new_hash, "updated_at": int(time.time())}},
        )
        return t("change_password_success", locale)

    async def get_profile(self, user_id: str, locale: str = "vi") -> dict:
        user = await self.db.users.find_one({"_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail=t("user_not_found", locale))
        return {
            "id": str(user["_id"]),
            "username": user.get("username"),
            "email": user.get("email"),
            "full_name": user.get("full_name") or user.get("username"),
            "phone": user.get("phone"),
            "avatar_url": user.get("avatar_url"),
            "role": user.get("role", "user"),
        }

    async def update_profile(self, user_id: str, req: UpdateProfileRequest, locale: str = "vi") -> dict:
        update_fields = {}
        if req.full_name is not None:
            update_fields["full_name"] = req.full_name
        if req.phone is not None:
            update_fields["phone"] = req.phone
        if req.avatar_url is not None:
            update_fields["avatar_url"] = req.avatar_url
        if req.email is not None:
            existing = await self.db.users.find_one({"email": req.email, "_id": {"$ne": user_id}})
            if existing:
                raise HTTPException(status_code=400, detail=t("email_exists", locale))
            update_fields["email"] = req.email

        if update_fields:
            update_fields["updated_at"] = int(time.time())
            await self.db.users.update_one({"_id": user_id}, {"$set": update_fields})

        return await self.get_profile(user_id, locale)

    async def refresh_token(self, refresh_token_str: str, locale: str = "vi") -> dict:
        try:
            payload = decode_token(refresh_token_str)
            if payload.get("type") != "refresh":
                raise HTTPException(status_code=400, detail=t("invalid_token", locale))
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=400, detail=t("invalid_token", locale))
            return {
                "accessToken": create_access_token(user_id),
                "refreshToken": create_refresh_token(user_id),
            }
        except Exception:
            raise HTTPException(status_code=401, detail=t("token_expired", locale))


mobile_auth_service = MobileAuthService()

