"""
Cấu hình hệ thống & Hằng số cốt lõi (Key Constants).
Phụ trách: Vũ (Core Infra)
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Runtime
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Database & Redis
    MONGO_URI: str = "mongodb://localhost:27017/?directConnection=true"
    DB_NAME: str = "quan4_culinary"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth & Security Constants
    JWT_SECRET: str = "dev_jwt_secret_change_in_prod"
    REFRESH_TOKEN_SECRET: str = "dev_refresh_secret_change_in_prod"
    SECRET_KEY: str = "dev_secret_key"
    FERNET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"
    # Cookie httpOnly (NFR-06). Chrome/Firefox/Edge chấp nhận Secure cookie trên localhost;.
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: str | None = None
    PII_RETENTION_DAYS: int = 180

    # Bootstrap
    SUPERADMIN_BOOTSTRAP_MODE: str = "auto"
    SUPERADMIN_EMAIL: str = "admin@quan4culinary.vn"
    SUPERADMIN_PASSWORD: str = "ChangeMe123!"

    # Content & Media Limits
    MAX_POI_IMAGES: int = 8
    MAX_IMAGE_SIZE_MB: int = 5

    # Audio & TTS Constants
    VOICE_CATALOG_TTL_HOURS: int = 6
    MAX_CONCURRENT_TTS: int = 3
    AUDIO_TASK_HEARTBEAT_SECONDS: int = 5
    AUDIO_TASK_STALE_AFTER_MINUTES: int = 5
    AUDIO_TASK_RETENTION_DAYS: int = 14

    # Localization & AI Constants
    ON_DEMAND_RATE_LIMIT_PER_10MIN: int = 30
    HOTSET_MAX_POI_IDS: int = 10
    OWNER_DAILY_LIMIT: int = 10
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Static Paths
    STATIC_DIR: str = "app/static"
    MAP_PACK_DATA_DIR: str = "app/static/maps"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in {"production", "prod"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
