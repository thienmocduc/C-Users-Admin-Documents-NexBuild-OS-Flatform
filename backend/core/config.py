"""Application configuration — loads from .env, NEVER hardcoded."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "NexBuild API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = ["https://nexbuild.holdings", "http://localhost:3000"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nexbuild"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_PRIVATE_KEY_PATH: str = "keys/private.pem"
    JWT_PUBLIC_KEY_PATH: str = "keys/public.pem"
    # Fallback for testing (HS256)
    JWT_SECRET_KEY: str = "dev-secret-change-in-production"

    # Rate Limiting
    LOGIN_RATE_LIMIT: int = 5          # per 15 min per IP
    LOGIN_LOCKOUT_MINUTES: int = 30
    API_RATE_LIMIT: int = 100          # per min per IP
    USER_RATE_LIMIT: int = 1000        # per hour per user

    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    ALLOWED_DOC_TYPES: list[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "text/csv",
    ]

    # S3 (for file uploads)
    S3_BUCKET: str = ""
    S3_REGION: str = "ap-southeast-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Fal.ai (image generation — server-side only, NEVER expose to client)
    FAL_API_KEY: str = ""

    # Escrow
    ESCROW_AUTO_RELEASE_DAYS: int = 30
    COMMISSION_SUPPLIER_PCT: float = 2.5
    COMMISSION_BOOKING_PCT: float = 8.0
    ESCROW_FEE_PCT: float = 0.5

    model_config = {"env_file": ".env", "case_sensitive": True}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
