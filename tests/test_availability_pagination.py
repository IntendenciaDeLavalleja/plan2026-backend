from datetime import date, time

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.availability import AppointmentSlot
from app.models.tribute_type import TributeType
from app.models.user import AdminUser


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    RATELIMIT_STORAGE_URI = "memory://"
    WTF_CSRF_ENABLED = False


def _client_with_slots():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        user = AdminUser(username="admin", email="admin@example.test", is_superuser=True)
        user.set_password("safe-password")
        tribute = TributeType(name="Contribución Urbana", slug="urbana", is_active=True)
        db.session.add_all([user, tribute])
        db.session.flush()
        db.session.add_all([
            AppointmentSlot(tribute_type_id=tribute.id, date=date(2026, 8, day), start_time=time(9, 0), end_time=time(10, 0), capacity=1)
            for day in (3, 4, 5, 6, 7)
        ])
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True
    return app, client


def test_slots_are_paginated_newest_first_by_default():
    app, client = _client_with_slots()
    response = client.get("/admin/api/availability/slots?page=1&per_page=2")

    assert response.status_code == 200
    data = response.json["data"]
    assert data["page"] == 1
    assert data["per_page"] == 2
    assert data["total"] == 5
    assert data["pages"] == 3
    assert [item["date"] for item in data["items"]] == ["2026-08-07", "2026-08-06"]

    with app.app_context():
        db.drop_all()


def test_slots_can_be_sorted_oldest_first_on_later_pages():
    app, client = _client_with_slots()
    response = client.get("/admin/api/availability/slots?page=2&per_page=2&sort=asc")

    assert response.status_code == 200
    data = response.json["data"]
    assert [item["date"] for item in data["items"]] == ["2026-08-05", "2026-08-06"]

    invalid = client.get("/admin/api/availability/slots?sort=random")
    assert invalid.status_code == 400
    assert invalid.json["error"]["code"] == "invalid_sort"

    with app.app_context():
        db.drop_all()
