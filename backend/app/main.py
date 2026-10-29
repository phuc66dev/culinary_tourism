from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI, Response, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.static_guard import GuardedStaticFiles

from app.core.config import settings
from app.core.database import close_db, connect_db, ping_db
from app.modules.admin.service import admin_service
from app.modules.audio.task_manager import audio_task_manager

# Import 10 Router Lanes
from app.modules.content.router import router as content_router
from app.modules.audio.router import router as audio_router
from app.modules.admin.router import router as admin_router
from app.modules.owner.router import router as owner_router
from app.modules.ai_advisor.router import router as ai_advisor_router
from app.modules.localization.router import router as localization_router
from app.modules.ui_i18n.router import router as ui_i18n_router
from app.modules.maps.router import router as maps_router
from app.modules.analytics.router import router as analytics_router
from app.modules.runtime_observability.router import router as runtime_observability_router


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

_INSECURE_DEFAULTS = {
    "dev_jwt_secret_change_in_prod",
    "dev_refresh_secret_change_in_prod",
    "dev_secret_key",
    "ChangeMe123!",
}


def assert_security_config() -> None:
    """Tầng 1 — Security & Bootstrap Guard: production không được chạy với secret mặc định/yếu."""
    if not settings.is_production:
        return
    problems = []
    for name in ("JWT_SECRET", "REFRESH_TOKEN_SECRET"):
        value = getattr(settings, name)
        if (value in _INSECURE_DEFAULTS or value.startswith(("change_me", "replace_with_"))
                or len(value) < 32):
            problems.append(f"{name} yếu/mặc định (cần >= 32 ký tự ngẫu nhiên)")
    if settings.JWT_SECRET == settings.REFRESH_TOKEN_SECRET:
        problems.append("JWT_SECRET và REFRESH_TOKEN_SECRET phải khác nhau")
    if (settings.SECRET_KEY in _INSECURE_DEFAULTS or
        settings.SECRET_KEY.startswith(("replace_with_", "change_me")) or
        len(settings.SECRET_KEY) < 32):
        problems.append("SECRET_KEY phải là chuỗi ngẫu nhiên >= 32 ký tự")
    if settings.SUPERADMIN_BOOTSTRAP_MODE.lower() == "auto" and (
        settings.SUPERADMIN_PASSWORD in _INSECURE_DEFAULTS
        or settings.SUPERADMIN_PASSWORD.startswith(("set_strong_", "replace_with_"))
        or len(settings.SUPERADMIN_PASSWORD) < 12
    ):
        problems.append("SUPERADMIN_PASSWORD chưa được thay bằng mật khẩu mạnh")
    if not settings.FERNET_KEY or settings.FERNET_KEY.startswith("replace_with_"):
        problems.append("FERNET_KEY phải là khóa Fernet đã tạo")
    else:
        try:
            from cryptography.fernet import Fernet
            Fernet(settings.FERNET_KEY.encode())
        except (ValueError, TypeError):
            problems.append("FERNET_KEY không hợp lệ")
    if not settings.COOKIE_SECURE:
        problems.append("COOKIE_SECURE phải là true ở production")
    if problems:
        raise RuntimeError("Cấu hình bảo mật không hợp lệ: " + "; ".join(problems))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Backend Startup Sequence (4 Tầng theo Kiến trúc):
    - Tầng 1: Security & Bootstrap Guard
    - Tầng 2: Database / Cache / Media Readiness (`connect_db`)
    - Tầng 3: Seeding Roles & SuperAdmin (`ensure_roles`, `ensure_super_admin`)
    - Tầng 4: Recovery Audio Tasks & Background Workers (Sprint 3 — Task 3.8)
    """
    assert_security_config()
    await connect_db()
    await admin_service.ensure_roles()
    await admin_service.ensure_super_admin()
    await audio_task_manager.recover()
    audio_task_manager.start_supervisor()  # Reclaim expired leases after a crash, not only at startup.
    yield
    await audio_task_manager.shutdown()
    await close_db()


_OPENAPI_TAGS = [
    {"name": "Health", "description": "Liveness / readiness probe."},
    {"name": "1. Content (POI)", "description": "**Bảo** — API công khai cho PWA du khách."},
    {"name": "2. Audio & TTS", "description": "**Vũ** — Sinh audio & giám sát tác vụ."},
    {
        "name": "3. Admin & Auth",
        "description": "**Vũ** — Đăng nhập (httpOnly Cookie, dùng chung Admin/Owner), RBAC, kiểm duyệt. "
        "Bấm **Authorize** để test bằng Bearer token; hoặc gọi `POST /admin/auth/login` ngay trên Swagger "
        "(trình duyệt tự giữ Cookie).",
    },
    {"name": "4. Owner Portal", "description": "**Phúc** — Cổng chủ quán."},
]

app = FastAPI(
    title="Hệ Thống Du Lịch Ẩm Thực Quận 4 — API",
    description="Full-stack Offline-First PWA Backend (FastAPI + MongoDB + Edge-TTS + Gemini AI)",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=_OPENAPI_TAGS,
)

# Cấu hình CORS cho phép gửi httpOnly Cookie từ Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def csrf_origin_guard(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and (
        request.cookies.get("access_token") or request.cookies.get("refresh_token")
        or request.url.path == "/api/v1/admin/auth/login"
    ):
        origin = request.headers.get("origin")
        if (origin and origin not in settings.cors_origin_list) or (
            not origin and settings.is_production
        ):
            return JSONResponse({"detail": "Nguồn yêu cầu không được phép (CSRF)"}, status_code=403)
    return await call_next(request)


# Mount thư mục tĩnh (/static/audio, /static/images, /static/maps)
static_path = Path(__file__).resolve().parent / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", GuardedStaticFiles(directory=str(static_path)), name="static")

# Mount 10 Router Lanes dưới prefix /api/v1
API_PREFIX = "/api/v1"
app.include_router(content_router, prefix=f"{API_PREFIX}/poi", tags=["1. Content (POI)"])
app.include_router(audio_router, prefix=f"{API_PREFIX}/audio", tags=["2. Audio & TTS"])
app.include_router(admin_router, prefix=f"{API_PREFIX}/admin", tags=["3. Admin & Auth"])
app.include_router(owner_router, prefix=f"{API_PREFIX}/owner", tags=["4. Owner Portal"])
app.include_router(ai_advisor_router, prefix=f"{API_PREFIX}/ai", tags=["5. AI Advisor"])
app.include_router(localization_router, prefix=f"{API_PREFIX}/localizations", tags=["6. Localization"])
app.include_router(ui_i18n_router, prefix=f"{API_PREFIX}/ui-bundles", tags=["7. UI i18n Bundles"])
app.include_router(maps_router, prefix=f"{API_PREFIX}/maps", tags=["8. Offline Maps (PMTiles)"])
app.include_router(analytics_router, prefix=f"{API_PREFIX}/analytics", tags=["9. Privacy Analytics"])
app.include_router(
    runtime_observability_router,
    prefix=f"{API_PREFIX}/runtime",
    tags=["10. Runtime Observability"],
)


@app.get("/health", tags=["Health"])
@app.get(f"{API_PREFIX}/health", tags=["Health"], include_in_schema=False)  # alias theo PRD
async def health_check():
    """Liveness probe."""
    return {"status": "ok", "service": "quan4-culinary-backend"}


@app.get("/health/ready", tags=["Health"])
async def readiness_check(response: Response):
    """Readiness probe kiểm tra kết nối DB & Static Storage."""
    db_ok = await ping_db()
    static_ok = static_path.is_dir()
    if not (db_ok and static_ok):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if db_ok and static_ok else "degraded",
        "db": "connected" if db_ok else "unavailable",
        "static": "ok" if static_ok else "missing",
    }
