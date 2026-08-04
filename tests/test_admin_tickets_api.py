from __future__ import annotations

from datetime import date, time, timedelta

import pytest

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.appointment import Appointment
from app.models.availability import AppointmentSlot, Location
from app.models.ticket_event import TicketEvent
from app.models.tribute_type import TributeType
from app.models.user import AdminUser


class TicketsTestConfig(Config):
    TESTING = True
    SECRET_KEY = "tickets-test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    CORS_ALLOWED_ORIGINS = ["https://dashboard.test.example.com"]
    WTF_CSRF_ENABLED = False
    RATELIMIT_STORAGE_URI = "memory://"


@pytest.fixture()
def app():
    app = create_app(TicketsTestConfig)
    with app.app_context():
        db.create_all()
        admin = AdminUser(username="root", email="root@example.test", is_active=True, is_superuser=True)
        admin.set_password("safe-test-password")
        tribute = TributeType(name="Contribucion", slug="contribucion", is_active=True)
        location = Location(name="Centro", is_active=True)
        db.session.add_all([admin, tribute, location])
        db.session.commit()

        today = date.today()
        slot_10 = AppointmentSlot(
            tribute_type_id=tribute.id, location_id=location.id,
            date=today, start_time=time(10, 0), end_time=time(10, 30), capacity=5,
        )
        slot_11 = AppointmentSlot(
            tribute_type_id=tribute.id, location_id=location.id,
            date=today, start_time=time(11, 0), end_time=time(11, 30), capacity=5,
        )
        db.session.add_all([slot_10, slot_11])
        db.session.commit()

        def make(code, slot, name, status="reserved"):
            a = Appointment(
                reservation_code=code,
                tribute_type_id=tribute.id,
                location_id=location.id,
                slot_id=slot.id,
                citizen_name=name,
                citizen_document="1.234.567-8",
                phone="099123456",
                status=status,
            )
            db.session.add(a)
            return a

        a1 = make("T-0001", slot_10, "Ana Perez", "reserved")
        a2 = make("T-0002", slot_10, "Bruno Diaz", "called")
        a3 = make("T-0003", slot_11, "Carla Ruiz", "resolved")
        db.session.commit()
        db.session.refresh(a1)
        db.session.refresh(a2)
        db.session.refresh(a3)
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def admin_client(app, monkeypatch):
    client = app.test_client()
    monkeypatch.setattr("app.blueprints.admin.auth.send_2fa_email", lambda *_args: True)
    monkeypatch.setattr("app.blueprints.admin.auth.secrets.choice", lambda _digits: "1")
    client.get("/api/v1/admin/auth/captcha")
    with client.session_transaction() as session:
        answer = session["captcha_result"]
    assert client.post("/api/v1/admin/auth/login", json={
        "email": "root@example.test", "password": "safe-test-password", "captcha": str(answer),
    }).status_code == 200
    assert client.post("/api/v1/admin/auth/verify-2fa", json={"code": "111111"}).status_code == 200
    return client


def test_tickets_require_authentication(app):
    response = app.test_client().get("/api/v1/admin/tickets")
    assert response.status_code == 401
    assert response.content_type.startswith("application/json")


def test_list_today_tickets_and_filters(app, monkeypatch):
    client = admin_client(app, monkeypatch)
    data = client.get("/api/v1/admin/tickets").json["data"]
    assert data["total"] == 3
    assert {item["code"] for item in data["items"]} == {"T-0001", "T-0002", "T-0003"}

    hour = client.get("/api/v1/admin/tickets?hour=10").json["data"]
    assert hour["total"] == 2
    assert {item["code"] for item in hour["items"]} == {"T-0001", "T-0002"}

    status = client.get("/api/v1/admin/tickets?status=called").json["data"]
    assert status["total"] == 1
    assert status["items"][0]["code"] == "T-0002"

    search = client.get("/api/v1/admin/tickets?search=Ana").json["data"]
    assert search["total"] == 1
    assert search["items"][0]["code"] == "T-0001"


def test_ticket_detail_and_history(app, monkeypatch):
    client = admin_client(app, monkeypatch)
    with app.app_context():
        ticket_id = Appointment.query.filter_by(reservation_code="T-0002").first().id

    detail = client.get(f"/api/v1/admin/tickets/{ticket_id}").json["data"]
    assert detail["code"] == "T-0002"
    assert detail["status"] == "called"
    assert detail["person_name"] == "Bruno Diaz"

    history = client.get(f"/api/v1/admin/tickets/{ticket_id}/history").json["data"]
    assert history == []


def test_status_transitions_and_audit(app, monkeypatch):
    client = admin_client(app, monkeypatch)
    with app.app_context():
        ticket_id = Appointment.query.filter_by(reservation_code="T-0001").first().id

    called = client.patch(f"/api/v1/admin/tickets/{ticket_id}/status", json={"status": "called"})
    assert called.status_code == 200
    assert called.json["data"]["status"] == "called"

    invalid = client.patch(f"/api/v1/admin/tickets/{ticket_id}/status", json={"status": "resolved"})
    assert invalid.status_code == 400
    assert invalid.json["error"]["code"] == "invalid_transition"

    in_service = client.patch(f"/api/v1/admin/tickets/{ticket_id}/status", json={"status": "in_service", "note": "En ventanilla 2"})
    assert in_service.status_code == 200

    history = client.get(f"/api/v1/admin/tickets/{ticket_id}/history").json["data"]
    assert [e["to_status"] for e in history] == ["called", "in_service"]
    assert history[1]["note"] == "En ventanilla 2"
    assert history[1]["username"] == "root"


def test_current_hour_snapshot(app, monkeypatch):
    client = admin_client(app, monkeypatch)
    data = client.get("/api/v1/admin/tickets/current-hour").json["data"]
    assert data["date"] == date.today().isoformat()
    assert isinstance(data["hour"], int)
    assert "tickets" in data
    assert "called_ticket" in data
    assert "updated_at" in data


def test_dashboard_today_summary(app, monkeypatch):
    client = admin_client(app, monkeypatch)
    data = client.get("/api/v1/admin/dashboard/today").json["data"]
    assert data["total"] == 3
    assert data["buckets"]["pending"] == 1
    assert data["buckets"]["called"] == 1
    assert data["buckets"]["resolved"] == 1
    assert data["resolution_rate"] == pytest.approx(33.3, abs=0.1)
    assert data["top_service"] == "Contribucion"
    assert data["next_pending"]["code"] == "T-0001"


def test_csrf_token_endpoint(app):
    client = app.test_client()
    response = client.get("/api/v1/admin/auth/csrf-token")
    assert response.status_code == 200
    assert response.content_type.startswith("application/json")
    assert response.json["ok"] is True
    assert response.json["data"]["csrf_token"]
