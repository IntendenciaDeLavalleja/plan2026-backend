from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user import AdminUser


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    JWT_SECRET_KEY = "test-jwt-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    RATELIMIT_STORAGE_URI = "memory://"
    WTF_CSRF_ENABLED = False
    DEV_TWO_FACTOR_CODE = None
    CORS_ALLOWED_ORIGINS = ["https://plan2026.lavalleja.uy", "https://visualizer.plan2026.lavalleja.uy"]


def app():
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        user = AdminUser(username="admin", email="admin@example.test", is_superuser=True)
        user.set_password("safe-password")
        db.session.add(user)
        db.session.commit()
    return application


def _jwt_client(application, monkeypatch):
    client = application.test_client()
    monkeypatch.setattr("app.blueprints.admin.dashboard_auth.send_2fa_email", lambda *_args: True)
    monkeypatch.setattr("app.blueprints.admin.dashboard_auth.secrets.choice", lambda _digits: "1")
    first = client.post("/api/v1/admin/auth/login", json={"email": "admin@example.test", "password": "safe-password"})
    assert first.status_code == 200
    pending = first.json["data"]["pending_token"]
    second = client.post("/api/v1/admin/auth/verify-2fa", json={"code": "111111"}, headers={"Authorization": f"Bearer {pending}"})
    assert second.status_code == 200
    return client, second.json["data"]["access_token"]


def test_public_health_and_namespaces(monkeypatch):
    application = app()
    client = application.test_client()
    assert client.get("/healthz").json == {"status": "ok"}
    assert client.get("/api/v1/public/tribute-types").status_code == 200
    assert client.get("/api/v1/admin/dashboard/today").status_code == 401
    assert client.get("/admin").status_code == 302
    assert client.get("/admin/api/dashboard").status_code == 401


def test_dashboard_jwt_and_panel_session_are_isolated(monkeypatch):
    application = app()
    client, access = _jwt_client(application, monkeypatch)
    headers = {"Authorization": f"Bearer {access}"}
    assert client.get("/api/v1/admin/auth/me", headers=headers).status_code == 200
    assert client.get("/api/v1/admin/dashboard/today", headers=headers).status_code == 200
    assert client.get("/admin", headers=headers).status_code == 302
    assert client.get("/admin/api/dashboard", headers=headers).status_code == 401


def test_panel_flask_login_uses_its_own_session(monkeypatch):
    application = app()
    client = application.test_client()
    monkeypatch.setattr("app.blueprints.admin.auth.send_2fa_email", lambda *_args: True)
    monkeypatch.setattr("app.blueprints.admin.auth.secrets.choice", lambda _digits: "2")
    client.get("/admin/api/auth/captcha")
    with client.session_transaction() as session:
        answer = session["captcha_result"]
    assert client.post("/admin/api/auth/login", json={"email": "admin@example.test", "password": "safe-password", "captcha": str(answer)}).status_code == 200
    assert client.post("/admin/api/auth/verify-2fa", json={"code": "222222"}).status_code == 200
    assert client.get("/admin").status_code == 200
    assert client.get("/admin/api/dashboard").status_code == 200
    assert client.post("/admin/api/auth/logout").status_code == 200
    assert client.get("/admin").status_code == 302


def test_cors_for_bearer_api_has_no_credentials():
    response = app().test_client().options("/api/v1/admin/auth/login", headers={"Origin": "https://visualizer.plan2026.lavalleja.uy", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"})
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "https://visualizer.plan2026.lavalleja.uy"
    assert "Access-Control-Allow-Credentials" not in response.headers
