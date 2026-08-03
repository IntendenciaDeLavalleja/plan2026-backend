from app import create_app
from app.config import Config


FRONTEND_ORIGIN = "https://plan2026.lavalleja.uy"


class CorsTestConfig(Config):
    TESTING = True
    SECRET_KEY = "cors-test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    CORS_ALLOWED_ORIGINS = [FRONTEND_ORIGIN]
    WTF_CSRF_ENABLED = False


def _client():
    return create_app(CorsTestConfig).test_client()


def test_cors_allows_versioned_preflight_from_frontend():
    response = _client().options(
        "/api/v1/public/tribute-types",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == FRONTEND_ORIGIN
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert "GET" in response.headers["Access-Control-Allow-Methods"]
    assert "Origin" in response.headers["Vary"]


def test_cors_applies_to_authenticated_and_not_found_api_errors():
    client = _client()

    unauthorized = client.get("/api/v1/admin/auth/me", headers={"Origin": FRONTEND_ORIGIN})
    not_found = client.get("/api/v1/not-found", headers={"Origin": FRONTEND_ORIGIN})

    assert unauthorized.status_code == 401
    assert not_found.status_code == 404
    assert unauthorized.headers["Access-Control-Allow-Origin"] == FRONTEND_ORIGIN
    assert not_found.headers["Access-Control-Allow-Origin"] == FRONTEND_ORIGIN


def test_cors_does_not_allow_unlisted_origins():
    response = _client().options(
        "/api/v1/public/tribute-types",
        headers={
            "Origin": "https://sitio-no-autorizado.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "Access-Control-Allow-Origin" not in response.headers
