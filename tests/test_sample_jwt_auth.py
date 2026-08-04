from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user import AdminUser


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    RATELIMIT_STORAGE_URI = "memory://"
    DEV_TWO_FACTOR_CODE = None


def _app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        user = AdminUser(username="admin", email="admin@example.test", is_superuser=True)
        user.set_password("safe-password")
        db.session.add(user)
        db.session.commit()
    return app


def test_dashboard_bearer_flow_does_not_authenticate_html_panel(monkeypatch):
    app = _app()
    client = app.test_client()
    monkeypatch.setattr("app.blueprints.admin.auth.send_2fa_email", lambda *_args: None)
    monkeypatch.setattr("app.blueprints.admin.auth.secrets.choice", lambda _digits: "1")

    first = client.post("/api/admin/auth/login", json={"email": "admin@example.test", "password": "safe-password"})
    assert first.status_code == 200
    pending = first.json["data"]["pending_token"]
    verified = client.post("/api/admin/auth/verify-2fa", json={"code": "111111"}, headers={"Authorization": f"Bearer {pending}"})
    assert verified.status_code == 200
    access = verified.json["data"]["access_token"]
    assert client.get("/api/admin/auth/me", headers={"Authorization": f"Bearer {access}"}).status_code == 200
    assert client.get("/admin", headers={"Authorization": f"Bearer {access}"}).status_code == 302


def test_html_panel_uses_flask_login_session(monkeypatch):
    app = _app()
    client = app.test_client()
    monkeypatch.setattr("app.blueprints.admin.auth.send_2fa_email", lambda *_args: None)
    monkeypatch.setattr("app.blueprints.admin.auth.secrets.choice", lambda _digits: "2")
    client.get("/admin/captcha")
    with client.session_transaction() as session:
        answer = session["captcha_result"]
    assert client.post("/admin/login", json={"email": "admin@example.test", "password": "safe-password", "captcha": str(answer)}).status_code == 200
    assert client.post("/admin/verify-2fa", json={"code": "222222"}).status_code == 200
    assert client.get("/admin").status_code == 200
