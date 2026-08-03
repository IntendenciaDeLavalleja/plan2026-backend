from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user import AdminUser


class AdminAuthTestConfig(Config):
    TESTING = True
    SECRET_KEY = "admin-auth-test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    CORS_ALLOWED_ORIGINS = ["https://plan2026.lavalleja.uy"]


def _app():
    app = create_app(AdminAuthTestConfig)
    with app.app_context():
        db.create_all()
        user = AdminUser(
            username="admin-test",
            email="admin-test@example.com",
            is_active=True,
            is_superuser=True,
        )
        user.set_password("test-password")
        db.session.add(user)
        db.session.commit()
    return app


def test_login_template_uses_only_versioned_auth_endpoints():
    response = _app().test_client().get("/admin/login")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert "/api/v1/admin/auth/captcha" in page
    assert "/api/v1/admin/auth/login" in page
    assert "/api/v1/admin/auth/verify-2fa" in page
    assert "/api/admin/auth/" not in page


def test_admin_auth_returns_json_before_and_after_login(monkeypatch):
    app = _app()
    client = app.test_client()
    monkeypatch.setattr("app.blueprints.admin.auth.send_2fa_email", lambda *_args: True)
    monkeypatch.setattr("app.blueprints.admin.auth.secrets.choice", lambda _digits: "1")

    captcha = client.get("/api/v1/admin/auth/captcha")
    assert captcha.status_code == 200
    assert captcha.content_type.startswith("application/json")
    assert captcha.json["ok"] is True

    invalid_login = client.post("/api/v1/admin/auth/login", json={})
    assert invalid_login.status_code == 400
    assert invalid_login.content_type.startswith("application/json")
    assert invalid_login.json["error"]["code"] == "missing_fields"

    login = client.post(
        "/api/v1/admin/auth/login",
        json={
            "email": "admin-test@example.com",
            "password": "test-password",
            "captcha": str(captcha.json["data"]["answer"]),
        },
    )
    assert login.status_code == 200
    assert login.content_type.startswith("application/json")
    assert login.json["data"]["requires_2fa"] is True

    verification = client.post("/api/v1/admin/auth/verify-2fa", json={"code": "111111"})
    assert verification.status_code == 200
    assert verification.content_type.startswith("application/json")
    assert verification.json["data"]["user"]["email"] == "admin-test@example.com"

    current_user = client.get("/api/v1/admin/auth/me")
    assert current_user.status_code == 200
    assert current_user.content_type.startswith("application/json")
    assert current_user.json["data"]["user"]["username"] == "admin-test"


def test_versioned_protected_endpoint_does_not_redirect_to_login():
    response = _app().test_client().get("/api/v1/admin/auth/me")

    assert response.status_code == 401
    assert response.content_type.startswith("application/json")
    assert response.json["error"]["code"] == "unauthorized"
