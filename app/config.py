import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def _csv(name: str, default: str = "") -> list:
    raw = os.environ.get(name, default) or ""
    return [item.strip() for item in raw.split(",") if item.strip()]


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "change-me-please"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URI") or "sqlite:///agenda.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    # Mail
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 25))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "False").lower() == "true"
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "False").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "no-reply@lavalleja.gub.uy")

    # Frontend & CORS
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    CORS_ORIGINS = _csv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173")
    DASHBOARD_ALLOWED_ORIGIN = os.environ.get("DASHBOARD_ALLOWED_ORIGIN", "https://visualizer.plan2026.lavalleja.uy")
    if DASHBOARD_ALLOWED_ORIGIN not in CORS_ORIGINS:
        CORS_ORIGINS = [*CORS_ORIGINS, DASHBOARD_ALLOWED_ORIGIN]

    # Dashboard API authentication follows the sample's Bearer-token model.
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or SECRET_KEY
    DASHBOARD_JWT_ACCESS_HOURS = max(1, int(os.environ.get("DASHBOARD_JWT_ACCESS_HOURS", "14")))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=DASHBOARD_JWT_ACCESS_HOURS)
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # Reservation code prefix
    RESERVATION_CODE_PREFIX = os.environ.get("RESERVATION_CODE_PREFIX", "IDL-AF")

    # Rate limiting storage
    RATELIMIT_STORAGE_URI = os.environ.get(
        "RATELIMIT_STORAGE_URI",
        os.environ.get("REDIS_URL", "memory://")
    )

    # MinIO (optional)
    MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT")
    MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY")
    MINIO_SECURE = os.environ.get("MINIO_SECURE", "False").lower() == "true"
    MINIO_BUCKET_NAME = os.environ.get("MINIO_BUCKET_NAME", "agenda-uploads")

    # CSRF
    WTF_CSRF_SECRET_KEY = os.environ.get("WTF_CSRF_SECRET_KEY", "csrf-change-me")
    WTF_CSRF_ENABLED = True

    # Bootstrap admin
    BOOTSTRAP_ADMIN_USERNAME = os.environ.get("BOOTSTRAP_ADMIN_USERNAME", "admin")
    BOOTSTRAP_ADMIN_EMAIL = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "admin@lavalleja.gub.uy")
    BOOTSTRAP_ADMIN_PASSWORD = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "Admin1234!")

    # Development-only 2FA code. Leave empty outside local testing.
    DEV_TWO_FACTOR_CODE = os.environ.get("DEV_TWO_FACTOR_CODE") or None
