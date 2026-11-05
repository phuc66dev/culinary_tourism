from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from app.modules.mobile.dependencies import (
    get_current_user_optional,
    get_current_user_required,
)
from app.modules.mobile.schemas import (
    ChangePasswordRequest,
    DeviceLoginRequest,
    ForgotPasswordRequest,
    GoogleLoginRequest,
    ListeningHistoryCreate,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    VerifyRequest,
)
from app.modules.mobile.services import (
    mobile_auth_service,
    mobile_history_service,
    mobile_poi_service,
)
from app.modules.mobile.utils.response import success_response

TAG_MOBILE = ["Mobile Client (App)"]

router = APIRouter(tags=TAG_MOBILE)

# ==========================================
# 1. HOME / DASHBOARD
# ==========================================
@router.get("/home", summary="Dữ liệu trang chủ Mobile")
async def get_home():
    """Dữ liệu feed trang chủ mobile."""
    return success_response(
        message="Success",
        data={
            "title": "Ẩm Thực Đặc Sắc Quận 4",
            "banner_images": [
                "/static/images/banner_quan4.jpg"
            ],
            "announcements": [],
        },
    )


# ==========================================
# 2. AUTHENTICATION (10 Endpoints)
# ==========================================
auth_router = APIRouter(prefix="/auth")


@auth_router.post("/login", summary="Đăng nhập tài khoản")
async def login(
    payload: LoginRequest,
    accept_language: str = Header("vi"),
):
    locale = accept_language.split(",")[0].split("-")[0] if isinstance(accept_language, str) else "vi"
    data = await mobile_auth_service.authenticate_user(payload.email, payload.password, locale=locale)
    resp = success_response(message="Login success", data=data)
    resp["accessToken"] = data["accessToken"]
    resp["refreshToken"] = data["refreshToken"]
    return resp


@auth_router.post("/register", summary="Đăng ký tài khoản (Gửi OTP)")
async def register(
    payload: RegisterRequest,
    accept_language: str = Header("vi"),
):
    locale = accept_language.split(",")[0].split("-")[0] if isinstance(accept_language, str) else "vi"
    msg = await mobile_auth_service.register_request(payload, locale=locale)
    return success_response(message=msg)


@auth_router.post("/verify", summary="Xác thực OTP & Kích hoạt tài khoản")
async def verify(
    payload: VerifyRequest,
    accept_language: str = Header("vi"),
):
    locale = accept_language.split(",")[0].split("-")[0] if isinstance(accept_language, str) else "vi"
    data = await mobile_auth_service.verify_registration(payload.email, payload.otp, locale=locale)
    resp = success_response(message="Verify success", data=data)
    resp["accessToken"] = data["accessToken"]
    resp["refreshToken"] = data["refreshToken"]
    return resp


@auth_router.post("/forgot-password", summary="Quên mật khẩu (Gửi OTP)")
async def forgot_password(
    payload: ForgotPasswordRequest,
    accept_language: str = Header("vi"),
):
    locale = accept_language.split(",")[0].split("-")[0] if isinstance(accept_language, str) else "vi"
    msg = await mobile_auth_service.forgot_password(payload.email, locale=locale)
    return success_response(message=msg)


@auth_router.post("/reset-password", summary="Đặt lại mật khẩu mới với OTP")
async def reset_password(
    payload: ResetPasswordRequest,
    accept_language: str = Header("vi"),
):
    locale = accept_language.split(",")[0].split("-")[0] if isinstance(accept_language, str) else "vi"
    msg = await mobile_auth_service.reset_password(payload, locale=locale)
    return success_response(message=msg)


@auth_router.post("/change-password", summary="Đổi mật khẩu")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user_required),
    accept_language: str = Header("vi"),
):
    locale = accept_language.split(",")[0].split("-")[0] if isinstance(accept_language, str) else "vi"
    msg = await mobile_auth_service.change_password(
        str(current_user["_id"]), payload, locale=locale
    )
    return success_response(message=msg)


@auth_router.get("/me", summary="Lấy thông tin tài khoản hiện tại")
async def get_me(
    current_user: dict = Depends(get_current_user_required),
    accept_language: str = Header("vi"),
):
    locale = accept_language.split(",")[0].split("-")[0] if isinstance(accept_language, str) else "vi"
    profile = await mobile_auth_service.get_profile(str(current_user["_id"]), locale=locale)
    return success_response(message="Get profile success", data=profile)


@auth_router.post("/update-profile", summary="Cập nhật hồ sơ cá nhân")
async def update_profile(
    payload: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user_required),
    accept_language: str = Header("vi"),
):
    locale = accept_language.split(",")[0].split("-")[0] if isinstance(accept_language, str) else "vi"
    data = await mobile_auth_service.update_profile(
        str(current_user["_id"]), payload, locale=locale
    )
    return success_response(message="Update profile success", data=data)


@auth_router.post("/refresh", summary="Làm mới token (Refresh Token)")
async def refresh(
    payload: RefreshRequest,
    accept_language: str = Header("vi"),
):
    locale = accept_language.split(",")[0].split("-")[0] if isinstance(accept_language, str) else "vi"
    token_str = payload.refreshToken or payload.refresh_token or ""
    data = await mobile_auth_service.refresh_token(token_str, locale=locale)
    resp = success_response(message="Token refresh success", data=data)
    resp["accessToken"] = data["accessToken"]
    resp["refreshToken"] = data["refreshToken"]
    return resp


@auth_router.post("/login-device", summary="Đăng nhập khách bằng Device ID")
async def login_device(payload: DeviceLoginRequest):
    dev_id = payload.device_id or payload.deviceId or ""
    data = await mobile_auth_service.login_or_create_by_device(dev_id)
    resp = success_response(message="Device login success", data=data)
    resp["accessToken"] = data["accessToken"]
    resp["refreshToken"] = data["refreshToken"]
    return resp


@auth_router.post("/google-login", summary="Đăng nhập Google OAuth")
async def google_login(
    payload: GoogleLoginRequest,
    accept_language: str = Header("vi"),
):
    locale = accept_language.split(",")[0].split("-")[0] if isinstance(accept_language, str) else "vi"
    token = payload.idToken or payload.id_token or payload.token
    if not token:
        raise HTTPException(status_code=400, detail="idToken is required")
    data = await mobile_auth_service.login_with_google(token, locale=locale)
    resp = success_response(message="Login success", data=data)
    resp["accessToken"] = data["accessToken"]
    resp["refreshToken"] = data["refreshToken"]
    return resp


router.include_router(auth_router)


# ==========================================
# 3. POIS & CONTENT (Điểm ẩm thực & Thuyết minh)
# ==========================================
poi_router = APIRouter(prefix="/pois")


@poi_router.get("", summary="Danh sách điểm ẩm thực POIs (GPS, Tìm kiếm, Ưu tiên phát)")
async def get_pois(
    keyword: Optional[str] = Query(None, description="Tìm kiếm theo tên hoặc danh mục"),
    search: Optional[str] = Query(None, description="Tìm kiếm theo tên (alias)"),
    lat: Optional[float] = Query(None, description="Vĩ độ người dùng"),
    latitude: Optional[float] = Query(None, description="Vĩ độ (alias)"),
    lng: Optional[float] = Query(None, description="Kinh độ người dùng"),
    longitude: Optional[float] = Query(None, description="Kinh độ (alias)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    accept_language: str = Header("vi"),
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    locale = accept_language.split(",")[0].split("-")[0] if isinstance(accept_language, str) else "vi"
    user_id = str(current_user["_id"]) if current_user else None

    kw = search if search is not None else keyword
    user_lat = latitude if latitude is not None else lat
    user_lng = longitude if longitude is not None else lng

    items, total = await mobile_poi_service.get_pois(
        keyword=kw,
        lat=user_lat,
        lng=user_lng,
        limit=limit,
        offset=offset,
        language=locale,
        user_id=user_id,
        device_id=x_device_id,
    )
    return success_response(
        message="Get pois success",
        data={"items": items, "total": total},
    )


@poi_router.get("/{poi_id}", summary="Chi tiết điểm ẩm thực POI")
async def get_poi_detail(
    poi_id: str,
    accept_language: str = Header("vi"),
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    locale = accept_language.split(",")[0].split("-")[0] if isinstance(accept_language, str) else "vi"
    user_id = str(current_user["_id"]) if current_user else None

    poi = await mobile_poi_service.get_poi_by_id(
        poi_id, language=locale, user_id=user_id, device_id=x_device_id
    )
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    return success_response(message="Get poi detail success", data=poi)


@poi_router.get("/{poi_id}/content", summary="Nội dung thuyết minh (Text/Audio đa ngôn ngữ)")
async def get_poi_content(
    poi_id: str,
    accept_language: str = Header("vi"),
):
    locale = accept_language.split(",")[0].split("-")[0] if isinstance(accept_language, str) else "vi"
    content = await mobile_poi_service.get_content_with_fallback(poi_id, language=locale)
    return success_response(message="Success", data=content)


@poi_router.get("/{poi_id}/content/available-languages", summary="Ngôn ngữ thuyết minh khả dụng của POI")
async def get_available_languages(poi_id: str):
    languages = await mobile_poi_service.get_available_languages(poi_id)
    return success_response(
        message="Get available languages success",
        data={"languages": languages},
    )


router.include_router(poi_router)

# Alias route ẩn (/stalls) để tương thích ngược nếu app cũ còn gọi, include_in_schema=False để sạch Swagger
hidden_stall_router = APIRouter(prefix="/stalls", include_in_schema=False)
hidden_stall_router.add_api_route("", get_pois, methods=["GET"])
hidden_stall_router.add_api_route("/{poi_id}", get_poi_detail, methods=["GET"])
hidden_stall_router.add_api_route("/{poi_id}/content", get_poi_content, methods=["GET"])
hidden_stall_router.add_api_route("/{poi_id}/content/available-languages", get_available_languages, methods=["GET"])
router.include_router(hidden_stall_router)


# ==========================================
# 4. LISTENING HISTORY (Lịch sử nghe)
# ==========================================
history_router = APIRouter(prefix="/listening-history")


@history_router.post("", summary="Lưu lịch sử nghe audio của POI")
async def save_history(
    payload: ListeningHistoryCreate,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    user_id = str(current_user["_id"]) if current_user else None
    data = await mobile_history_service.save_listening_history(payload, user_id=user_id)
    return success_response(message="Success", data=data)


@history_router.get("", summary="Xem danh sách lịch sử nghe POIs")
async def get_history(
    page: Optional[int] = Query(None, ge=1),
    size: Optional[int] = Query(None, ge=1, le=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    accept_language: str = Header("vi"),
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    locale = accept_language.split(",")[0].split("-")[0] if isinstance(accept_language, str) else "vi"
    user_id = str(current_user["_id"]) if current_user else None

    if not user_id and not x_device_id:
        raise HTTPException(status_code=401, detail="Yêu cầu đăng nhập hoặc cung cấp X-Device-Id")

    calc_skip = (page - 1) * size if page is not None and size is not None else skip
    calc_limit = size if size is not None else limit

    data = await mobile_history_service.get_listening_history(
        user_id=user_id,
        device_id=x_device_id,
        skip=calc_skip,
        limit=calc_limit,
        language=locale,
    )
    resp = success_response(message="Success", data=data)
    resp["items"] = data.get("items", [])
    resp["total"] = data.get("total", 0)
    return resp


router.include_router(history_router)
