from app import create_app
from app.config import Config


class HealthTestConfig(Config):
    TESTING = True
    SECRET_KEY = "health-test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///unavailable/path/agenda.db"
    RATELIMIT_STORAGE_URI = "redis://127.0.0.1:1/0"
    WTF_CSRF_ENABLED = False


def test_healthz_is_a_dependency_independent_liveness_check():
    response = create_app(HealthTestConfig).test_client().get("/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}