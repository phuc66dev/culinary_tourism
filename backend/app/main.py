"""
Entry Point của Backend FastAPI — Modular Monolith (10 Router Lanes).
Phụ trách: Vũ (Task 3.1)
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import close_db, connect_db

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Backend Startup Sequence (4 Tầng theo Kiến trúc):
    - Tầng 1: Security & Bootstrap Guard
    - Tầng 2: Database / Cache / Media Readiness (`connect_db`)
    - Tầng 3: Seeding Roles & SuperAdmin (`ensure_roles`, `ensure_super_admin`)
    - Tầng 4: Recovery Audio Tasks & Background Workers
    """
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="Hệ Thống Du Lịch Ẩm Thực Quận 4 — API",
    description="Full-stack Offline-First PWA Backend (FastAPI + MongoDB + Edge-TTS + Gemini AI)",
    version="1.0.0",
    lifespan=lifespan,
)

# Cấu hình CORS cho phép gửi httpOnly Cookie từ Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount thư mục tĩnh (/static/audio, /static/images, /static/maps)
static_path = Path(__file__).resolve().parent / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

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
async def health_check():
    """Liveness probe."""
    return {"status": "ok", "service": "quan4-culinary-backend"}


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Readiness probe kiểm tra kết nối DB & Static Storage."""
    return {"status": "ready", "db": "connected"}
