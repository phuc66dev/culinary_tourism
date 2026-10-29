from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Literal

from app.modules.admin.registrations import list_registrations, reveal_cccd, review_registration
from app.modules.admin.poi_management import (list_pois, create_poi as create_master_poi,
                                               get_poi as get_master_poi, update_poi as update_master_poi,
                                               delete_poi as delete_master_poi, save_english as save_poi_english)
from app.modules.admin.submissions import list_submissions, review_submission
from app.modules.admin.audio_preview import list_poi_audio_files, get_poi_audio_file
from app.modules.audio.sse import audio_tasks_event_stream
from app.modules.audio.task_manager import ActiveTaskExists, audio_task_manager
from app.modules.audio.task_store import audio_task_store
from app.modules.audio.manual_translation import save_task_manual_translation

from app.core.config import settings
from app.core.database import get_db, mongo_transaction
from app.core.auth_sessions import issue_tokens, rotate_tokens, revoke_refresh, revoke_all_sessions, revoke_access_session
from app.core.cache import login_attempt_allowed, login_attempt_clear
from app.core.security import hash_password, verify_password
import asyncio
from bson import ObjectId
from datetime import timezone
from app.modules.admin import identity_management as identity
from app.core.rbac import require_permission
from app.core.security import (
    REFRESH_COOKIE,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    load_user_context,
    set_auth_cookies,
)
from app.modules.admin.schemas import (
    LoginRequest,
    LoginResponse,
    MessageResponse,
    OwnerRegisterRequest,
    RefreshRequest,
    ReviewDecisionRequest,
    POICreateRequest,
    POIUpdateRequest,
    EnglishLocalizationRequest,
    UserMe, ChangePasswordRequest, UserCreateRequest, UserUpdateRequest,
    ResetPasswordRequest, RoleCreateRequest, RoleUpdateRequest,
)
from app.modules.admin.service import admin_service
from app.modules.admin.audit import list_audit_events, fingerprint_login, write_audit_event
from datetime import datetime

router = APIRouter()


# ==========================================
# 1. Authentication & Public Owner Register
# ==========================================
def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _dev_tokens(access: str, refresh: str) -> dict:
    """Token trong body chỉ để test ở môi trường dev."""
    return {"access_token": access, "refresh_token": refresh} if not settings.is_production else {}


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="Đăng nhập (Admin & Chủ quán dùng chung)",
    responses={401: {"description": "Sai email hoặc mật khẩu / tài khoản bị khóa"}},
)
async def login(payload: LoginRequest, request: Request, response: Response):
    """
    Xác thực và gắn httpOnly Cookie `access_token` (30 phút) + `refresh_token` (7 ngày).
    Dùng chung cho mọi vai trò — Frontend điều hướng theo `user.role` / `user.permissions`.
    """
    if not await login_attempt_allowed(payload.email, _client_ip(request)):
        await write_audit_event(None, "auth.login_rate_limited", "auth:login", _client_ip(request),
                                {"login_fingerprint": fingerprint_login(payload.email)})
        raise HTTPException(429, "Quá nhiều lần thử đăng nhập. Vui lòng thử lại sau.")
    user = await admin_service.authenticate(payload.email, payload.password)
    if user is None:
        await write_audit_event(
            None, "auth.login_failed", "auth:login", _client_ip(request),
            {"login_fingerprint": fingerprint_login(payload.email)}
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email hoặc mật khẩu không đúng")
    await login_attempt_clear(payload.email, _client_ip(request))
    # Session creation and audit MUST commit together; never issue a cookie
    # for an unaudited login.
    async with mongo_transaction() as tx:
        access, refresh = await issue_tokens(user, session=tx)
        await write_audit_event(str(user["_id"]), "auth.login",
                                f"user:{user['_id']}", _client_ip(request), session=tx)
    set_auth_cookies(response, access, refresh)
    ctx = await load_user_context(str(user["_id"]))
    return {"user": ctx, **_dev_tokens(access, refresh)}


@router.post(
    "/auth/refresh",
    response_model=LoginResponse,
    summary="Cấp lại access_token từ refresh_token",
    responses={401: {"description": "Refresh token thiếu / hết hạn / không hợp lệ"}},
)
async def refresh_session(response: Response, request: Request, body: RefreshRequest | None = None):
    """Đọc `refresh_token` từ Cookie (hoặc body khi test), xoay vòng cả hai token."""
    token = request.cookies.get(REFRESH_COOKIE) or (body.refresh_token if body else None)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Thiếu refresh token")
    claims = decode_token(token, "refresh")
    user = await admin_service.get_user_by_id(claims["sub"])
    if user is None or not user.get("is_active", True):
        clear_auth_cookies(response)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tài khoản không tồn tại hoặc đã bị khóa")
    # Refresh rotation and security event must be atomic.
    async with mongo_transaction() as tx:
        access, refresh = await rotate_tokens(token, user, session=tx)
        await write_audit_event(str(user["_id"]), "auth.refresh",
                                f"user:{user['_id']}", _client_ip(request), session=tx)
    set_auth_cookies(response, access, refresh)
    ctx = await load_user_context(str(user["_id"]))
    return {"user": ctx, **_dev_tokens(access, refresh)}


@router.post("/auth/logout", response_model=MessageResponse, summary="Đăng xuất (xóa Cookie)")
async def logout(response: Response, request: Request):
    """Xóa Cookie và ghi sự kiện đăng xuất (kể cả khi token đã hết hạn)."""
    user_id = None
    authorization = request.headers.get("authorization", "")
    token = request.cookies.get("access_token") or (authorization[7:].strip() if authorization.lower().startswith("bearer ") else None)
    if token:
        try:
            user_id = decode_token(token, "access")["sub"]
        except HTTPException:
            pass
    async with mongo_transaction() as tx:
        await revoke_refresh(request.cookies.get(REFRESH_COOKIE), session=tx)
        await revoke_access_session(token, session=tx)
        await write_audit_event(user_id, "auth.logout",
                                f"user:{user_id}" if user_id else "auth:logout",
                                _client_ip(request), session=tx)
    clear_auth_cookies(response)
    return {"message": "Đã đăng xuất"}


@router.get(
    "/auth/me",
    response_model=UserMe,
    summary="Tài khoản hiện tại + danh sách permissions",
    responses={401: {"description": "Chưa đăng nhập / token hết hạn"}},
)
async def get_me(user: dict = Depends(get_current_user)):
    """Frontend gọi khi tải trang để khôi phục phiên; nhận 401 thì thử `/auth/refresh` một lần."""
    return user


@router.post("/auth/change-password", response_model=MessageResponse)
async def change_password(payload: ChangePasswordRequest, request: Request, response: Response,
                          current: dict = Depends(get_current_user)):
    """Current password required. Revoke ALL sessions and bump token_version atomically."""
    db = get_db()
    user_id = current["id"]
    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not user or not await asyncio.to_thread(verify_password, payload.current_password, user["password_hash"]):
        raise HTTPException(400, "Mật khẩu hiện tại không đúng")
    if payload.current_password == payload.new_password:
        raise HTTPException(422, "Mật khẩu mới phải khác mật khẩu hiện tại")
    hashed = await asyncio.to_thread(hash_password, payload.new_password)
    async with mongo_transaction() as tx:
        updated = await db["users"].update_one(
            {"_id": user["_id"], "password_hash": user["password_hash"]},
            {"$set": {"password_hash": hashed, "must_change_password": False,
                      "updated_at": datetime.now(timezone.utc)}, "$inc": {"token_version": 1}}, session=tx)
        if not updated.modified_count:
            raise HTTPException(409, "Mật khẩu đã được thay đổi ở thiết bị khác")
        await revoke_all_sessions(user_id, session=tx)
        from app.modules.admin.audit import write_audit_event
        await write_audit_event(user_id, "auth.change_password", f"user:{user_id}", _client_ip(request), session=tx)
    clear_auth_cookies(response)
    return {"message": "Đổi mật khẩu thành công. Vui lòng đăng nhập lại."}


@router.post("/auth/register-owner")
async def register_owner(payload: OwnerRegisterRequest):
    return {"status": "todo", "endpoint": "POST /api/v1/admin/auth/register-owner"}


# ==========================================
# 2. POI Management & Activation Gate
# ==========================================
@router.get("/pois")
async def list_admin_pois(
    q: str | None = Query(None, max_length=100),
    ward: str | None = Query(None, max_length=80),
    is_active: bool | None = None,
    limit: int = Query(100, ge=1, le=200),
    skip: int = Query(0, ge=0),
    _: dict = Depends(require_permission("poi:read")),
):
    return await list_pois(q, ward, is_active, limit, skip)


@router.post("/pois", status_code=201)
async def create_poi(payload: POICreateRequest, request: Request,
                     user: dict = Depends(require_permission("poi:create"))):
    return await create_master_poi(payload, user, _client_ip(request))


@router.get("/pois/{poi_id}/audios")
async def get_admin_poi_audios(
    poi_id: str, _: dict = Depends(require_permission("poi:read")),
):
    """Preview all 5 current language MP3 files for a POI (including older jobs)."""
    response = await list_poi_audio_files(poi_id)
    return JSONResponse(response, headers={"Cache-Control": "no-store"})


@router.get("/pois/{poi_id}/audios/{lang}/play")
async def play_admin_poi_audio(
    poi_id: str, lang: str, _: dict = Depends(require_permission("poi:read")),
):
    """Stream an existing verified MP3 inline in the Admin player.

    Unlike the public /static link, the media URL is derived from the current
    localization and validated on disk. Browsers can seek through FileResponse
    (Range support in Starlette) and do not navigate to a new page.
    """
    file = await get_poi_audio_file(poi_id, lang)
    return FileResponse(
        file, media_type="audio/mpeg", filename=f"quan4_{poi_id}_{lang}.mp3",
        content_disposition_type="inline",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/pois/{poi_id}/audios/{lang}/download")
async def download_admin_poi_audio(
    poi_id: str, lang: str, _: dict = Depends(require_permission("poi:read")),
):
    """Force download of a validated audio file, not a user-supplied path."""
    file = await get_poi_audio_file(poi_id, lang)
    return FileResponse(
        file, media_type="audio/mpeg", filename=f"quan4_{poi_id}_{lang}.mp3",
        content_disposition_type="attachment", headers={
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox; default-src 'none'",
        },
    )


@router.get("/pois/{poi_id}")
async def get_admin_poi(poi_id: str, _: dict = Depends(require_permission("poi:read"))):
    return await get_master_poi(poi_id)


@router.patch("/pois/{poi_id}")
async def update_admin_poi(poi_id: str, payload: POIUpdateRequest, request: Request,
                           user: dict = Depends(require_permission("poi:update"))):
    # Activation requires poi:toggle permission as well as poi:update.
    if payload.is_active is not None and "poi:toggle" not in user["permissions"]:
        raise HTTPException(403, "Thiếu quyền poi:toggle")
    return await update_master_poi(poi_id, payload, user, _client_ip(request))


@router.put("/pois/{poi_id}/localizations/en")
async def update_english_localization(poi_id: str, payload: EnglishLocalizationRequest,
                                      request: Request, user: dict = Depends(require_permission("poi:update"))):
    return await save_poi_english(poi_id, payload, user, _client_ip(request))


@router.delete("/pois/{poi_id}")
async def delete_admin_poi(poi_id: str, request: Request,
                           user: dict = Depends(require_permission("poi:delete"))):
    return await delete_master_poi(poi_id, user, _client_ip(request))


# ==========================================
# 3. Kiểm duyệt Đơn Chủ Quán & POI Submissions
# ==========================================
@router.get("/registrations")
async def list_owner_registrations(
    status_filter: str | None = Query(None, alias="status", description="pending | approved | rejected"),
    q: str | None = Query(None, max_length=100, description="Tìm theo tên chủ quán / tên quán / SĐT / email"),
    limit: int = Query(100, ge=1, le=200),
    skip: int = Query(0, ge=0),
    _: dict = Depends(require_permission("user:read")),
):
    """Danh sách hồ sơ đăng ký (không chứa CCCD) + số lượng theo trạng thái."""
    return await list_registrations(status_filter, q, limit, skip)


@router.get("/registrations/{reg_id}/cccd")
async def show_owner_cccd(
    reg_id: str,
    request: Request,
    response: Response,
    user: dict = Depends(require_permission("user:update")),
):
    """Giải mã CCCD để đối chiếu — mỗi lần gọi đều ghi audit log; không cho cache."""
    response.headers["Cache-Control"] = "no-store"
    return await reveal_cccd(reg_id, user, _client_ip(request))


@router.post("/registrations/{reg_id}/review")
async def review_owner_registration(
    reg_id: str,
    decision: ReviewDecisionRequest,
    request: Request,
    user: dict = Depends(require_permission("user:update")),
):
    """Phê duyệt (bật `is_poi_owner_verified`) hoặc Từ chối (bắt buộc `admin_note`)."""
    return await review_registration(reg_id, decision.action, decision.admin_note, user, _client_ip(request))


@router.get("/submissions")
async def list_poi_submissions(
    status_filter: str | None = Query(None, alias="status"),
    q: str | None = Query(None, max_length=100),
    limit: int = Query(100, ge=1, le=200),
    skip: int = Query(0, ge=0),
    _: dict = Depends(require_permission("poi:read")),
):
    return await list_submissions(status_filter, q, limit, skip)


@router.post("/submissions/{sub_id}/review")
async def review_poi_submission(
    sub_id: str,
    decision: ReviewDecisionRequest,
    request: Request,
    user: dict = Depends(require_permission("poi:approve")),
):
    return await review_submission(sub_id, decision.action, decision.admin_note,
                                   decision.expected_revision, user, _client_ip(request))


# ==========================================
# 4. Audio Tasks & SSE Stream (Task 3.8, 3.9)
# ==========================================
class AudioTaskCreateRequest(BaseModel):
    poi_id: str = Field(min_length=24, max_length=24)
    languages: list[Literal["vi", "en", "zh", "ja", "ko"]] | None = Field(default=None, min_length=1)


@router.get("/audio-tasks")
async def list_audio_tasks(_: dict = Depends(require_permission("poi:update"))):
    return {"items": await audio_task_store.list()}


@router.get("/audio-tasks/stream")
async def stream_audio_tasks(request: Request, _: dict = Depends(require_permission("poi:update"))):
    """SSE: đẩy danh sách tác vụ audio theo thời gian thực (event `tasks`)."""
    return StreamingResponse(
        audio_tasks_event_stream(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.post("/audio-tasks", status_code=status.HTTP_202_ACCEPTED)
async def create_audio_task(
    payload: AudioTaskCreateRequest, request: Request, user: dict = Depends(require_permission("poi:update"))
):
    """Xếp hàng sinh audio (dịch + TTS) cho một quán. Body: {"poi_id": "...", "languages": ["en", ...]}."""
    try:
        task_id = await audio_task_manager.enqueue_poi_audio_task(
            payload.poi_id, payload.languages, actor_id=user["id"], actor_ip=_client_ip(request),
        )
    except ActiveTaskExists as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, {"message": str(exc), "task_id": exc.task_id}) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"id": task_id, "status": "queued"}


@router.post("/audio-tasks/{task_id}/{action}")
async def control_audio_task(
    task_id: str, action: str, request: Request, user: dict = Depends(require_permission("poi:update"))
):
    """Điều khiển tác vụ: action = pause | resume | cancel."""
    if action not in ("pause", "resume", "cancel", "retry"):
        raise HTTPException(422, "action must be pause, resume, cancel or retry")
    try:
        result = await audio_task_manager.control(
            task_id, action, actor_id=user["id"], actor_ip=_client_ip(request),
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "Task not found")
    return result


class ManualAudioTranslationRequest(BaseModel):
    model_config = {"extra": "forbid", "str_strip_whitespace": True}
    title: str = Field(min_length=1, max_length=180)
    description: str = Field(min_length=1, max_length=8000)


@router.put("/audio-tasks/{task_id}/translations/{lang}")
async def set_manual_audio_translation(
    task_id: str, lang: str, payload: ManualAudioTranslationRequest,
    request: Request, user: dict = Depends(require_permission("poi:update")),
):
    """Admin supplies a reviewed translation when Google remains rate-limited.

    Saving pauses the queued job; Admin fills remaining languages and presses Resume.
    """
    return await save_task_manual_translation(
        task_id, lang, payload.title, payload.description, user["id"], _client_ip(request),
    )


# ==========================================
# 5. Users, Roles & Audit Logs
# ==========================================
@router.get("/users")
async def list_users(q: str | None = Query(None, max_length=100), role: str | None = None,
                     limit: int = Query(50, ge=1, le=100), skip: int = Query(0, ge=0),
                     _: dict = Depends(require_permission("user:read"))):
    return await identity.list_users(q, role, limit, skip)


@router.post("/users", status_code=201)
async def create_user(payload: UserCreateRequest, request: Request,
                      actor: dict = Depends(require_permission("user:create"))):
    return await identity.create_user(payload, actor, _client_ip(request))


@router.patch("/users/{user_id}")
async def update_user(user_id: str, payload: UserUpdateRequest, request: Request,
                      actor: dict = Depends(require_permission("user:update"))):
    return await identity.update_user(user_id, payload, actor, _client_ip(request))


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, request: Request,
                      actor: dict = Depends(require_permission("user:delete"))):
    return await identity.delete_user(user_id, actor, _client_ip(request))


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(user_id: str, payload: ResetPasswordRequest, request: Request,
                              actor: dict = Depends(require_permission("user:update"))):
    return await identity.reset_password(user_id, payload, actor, _client_ip(request))


@router.get("/roles")
async def list_roles(_: dict = Depends(require_permission("role:read"))):
    return await identity.list_roles()


@router.post("/roles", status_code=201)
async def create_role(payload: RoleCreateRequest, request: Request,
                      actor: dict = Depends(require_permission("role:create"))):
    return await identity.create_role(payload, actor, _client_ip(request))


@router.patch("/roles/{name}")
async def update_role(name: str, payload: RoleUpdateRequest, request: Request,
                      actor: dict = Depends(require_permission("role:update"))):
    return await identity.update_role(name, payload, actor, _client_ip(request))


@router.delete("/roles/{name}")
async def delete_role(name: str, request: Request,
                      actor: dict = Depends(require_permission("role:delete"))):
    return await identity.delete_role(name, actor, _client_ip(request))


@router.get("/audit-logs")
async def list_audit_logs(
    q: str | None = Query(None, max_length=100),
    action: str | None = Query(None, max_length=100),
    user_id: str | None = Query(None, max_length=64),
    resource: str | None = Query(None, max_length=200),
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    _: dict = Depends(require_permission("audit:read")),
):
    """Nhật ký bất biến, mới nhất trước; hỗ trợ tìm kiếm/lọc/phân trang."""
    return await list_audit_events(q, action, user_id, from_time, to_time, limit, skip, resource=resource)
