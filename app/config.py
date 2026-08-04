import os
from dotenv import load_dotenv

load_dotenv()


def _origins(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default) or ""
    return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "change-me-please"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    TRUST_PROXY_HEADERS = os.environ.get("TRUST_PROXY_HEADERS", "False").lower() == "true"
    TRUST_PROXY_COUNT = int(os.environ.get("TRUST_PROXY_COUNT", 1))
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
    MAIL_DEBUG = os.environ.get("MAIL_DEBUG", "False").lower() == "true"
    MAIL_TIMEOUT = int(os.environ.get("MAIL_TIMEOUT", 8))

    # Frontend & CORS
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    CORS_ALLOWED_ORIGINS = _origins("CORS_ALLOWED_ORIGINS", "https://plan2026.lavalleja.uy")
    DASHBOARD_ALLOWED_ORIGIN = (os.environ.get("DASHBOARD_ALLOWED_ORIGIN") or "").strip().rstrip("/")
    if DASHBOARD_ALLOWED_ORIGIN and DASHBOARD_ALLOWED_ORIGIN not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS = [*CORS_ALLOWED_ORIGINS, DASHBOARD_ALLOWED_ORIGIN]

    # Reservation code prefix
    RESERVATION_CODE_PREFIX = os.environ.get("RESERVATION_CODE_PREFIX", "IDL-AF")

    # Fixed booking rules. These are application constants, not admin settings.
    MAX_RESERVATIONS_PER_DOCUMENT = 1
    MIN_ANTICIPATION_HOURS = 1
    MAX_ANTICIPATION_DAYS = 90

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
    WTF_CSRF_ENABLED = os.environ.get("WTF_CSRF_ENABLED", "True").lower() == "true"
    WTF_CSRF_HEADERS = ["X-CSRFToken", "X-CSRF-Token"]
