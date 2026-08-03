from __future__ import annotations

import re
from datetime import date, time, timedelta

import pytest

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.availability import AppointmentSlot, Location
from app.models.tribute_type import TributeType
from app.models.user import AdminUser


class IntegrationConfig(Config):
    TESTING = True
    SECRET_KEY = "integration-test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    CORS_ALLOWED_ORIGINS = ["https://plan2026.lavalleja.uy"]
    WTF_CSRF_ENABLED = False
    RATELIMIT_STORAGE_URI = "memory://"


@pytest.fixture()
def app():
    app = create_app(IntegrationConfig)
    with app.app_context():
        db.create_all()
        admin = AdminUser(username="root", email="root@example.test", is_active=True, is_superuser=True)
        admin.set_password("safe-test-password")
        operator = AdminUser(username="operator", email="operator@example.test", is_active=True, is_superuser=False)
        operator.set_password("safe-test-password")
        tribute = TributeType(name="Contribucion", slug="contribucion", is_active=True)
        location = Location(name="Centro", is_active=True)
        db.session.add_all([admin, operator, tribute, location])
        db.session.commit()
        future = date.today() + timedelta(days=2)
        db.session.add_all([
            AppointmentSlot(
                tribute_type_id=tribute.id,
                location_id=location.id,
                date=future,
                start_time=time(10, 0),
                end_time=time(10, 30),
                capacity=1,
            ),
            AppointmentSlot(
                tribute_type_id=tribute.id,
                location_id=location.id,
                date=future,
                start_time=time(11, 0),
                end_time=time(11, 30),
                capacity=2,
            ),
        ])
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def admin_client(app, monkeypatch, email="root@example.test"):
    client = app.test_client()
    monkeypatch.setattr("app.blueprints.admin.auth.send_2fa_email", lambda *_args: True)
    monkeypatch.setattr("app.blueprints.admin.auth.secrets.choice", lambda _digits: "1")
    captcha = client.get("/api/v1/admin/auth/captcha")
    with client.session_transaction() as session:
        answer = session["captcha_result"]
    assert client.post("/api/v1/admin/auth/login", json={
        "email": email, "password": "safe-test-password", "captcha": str(answer),
    }).status_code == 200
    assert client.post("/api/v1/admin/auth/verify-2fa", json={"code": "111111"}).status_code == 200
    return client


def envelope(response, status):
    assert response.status_code == status
    assert response.content_type.startswith("application/json")
    assert response.json["ok"] is (status < 400)
    return response.json["data"] if status < 400 else response.json["error"]


def booking_payload(tribute_id, slot_id, document="4.548.541-3"):
    return {
        "tribute_type_id": tribute_id,
        "slot_id": slot_id,
        "citizen_name": "Persona de Prueba",
        "citizen_document": document,
        "phone": "099 123 456",
        "email": "persona@example.test",
        "accept_terms": True,
    }


def test_api_errors_are_json_and_csrf_is_enforced_when_enabled(app):
    client = app.test_client()
    envelope(client.get("/api/v1/admin/dashboard"), 401)
    assert client.get("/api/v1/missing").json["error"]["code"] == "not_found"
    assert client.get("/api/v1/missing").content_type.startswith("application/json")
    assert client.post("/api/v1/public/tribute-types").status_code == 405
    assert client.post("/api/v1/public/tribute-types").content_type.startswith("application/json")

    app.config["WTF_CSRF_ENABLED"] = True
    login = client.get("/admin/login")
    token = re.search(r'<meta name="csrf-token" content="([^"]+)"', login.get_data(as_text=True)).group(1)
    rejected = client.post("/api/v1/admin/auth/login", json={})
    assert rejected.status_code == 400
    assert rejected.json["error"]["code"] == "csrf_failed"
    accepted = client.post("/api/v1/admin/auth/login", json={}, headers={"X-CSRFToken": token})
    assert accepted.status_code == 400
    assert accepted.json["error"]["code"] == "missing_fields"


def test_public_booking_flow_is_consistent_and_safe(app):
    client = app.test_client()
    with app.app_context():
        tribute = TributeType.query.filter_by(slug="contribucion").first()
        first_slot, second_slot = AppointmentSlot.query.order_by(AppointmentSlot.start_time).all()

    envelope(client.get("/api/v1/public/tribute-types"), 200)
    dates = envelope(client.get(f"/api/v1/public/availability?tribute_type_id={tribute.id}&days=45"), 200)
    assert dates["dates"] and dates["dates"][0]["remaining"] == 3
    slots = envelope(client.get(f"/api/v1/public/slots?tribute_type_id={tribute.id}&date={first_slot.date.isoformat()}"), 200)
    assert len(slots["slots"]) == 2

    created = envelope(client.post("/api/v1/public/appointments", json=booking_payload(tribute.id, first_slot.id)), 201)
    assert created["reservation_code"]
    duplicate = client.post("/api/v1/public/appointments", json=booking_payload(tribute.id, second_slot.id, "45485413"))
    assert duplicate.status_code == 409
    assert duplicate.json["error"]["code"] == "max_per_document"
    assert client.post(f"/api/v1/public/appointments/{created['reservation_code']}/cancel", json={}).json["error"]["code"] == "missing_document"
    wrong_document = client.post(f"/api/v1/public/appointments/{created['reservation_code']}/cancel", json={"document": "1.111.111-1"})
    assert wrong_document.status_code == 404
    envelope(client.post(f"/api/v1/public/appointments/{created['reservation_code']}/cancel", json={"document": "45485413"}), 200)
    with app.app_context():
        assert db.session.get(AppointmentSlot, first_slot.id).reserved_count == 0


def test_admin_crud_reschedule_and_access_controls(app, monkeypatch):
    client = admin_client(app, monkeypatch)
    with app.app_context():
        tribute = TributeType.query.filter_by(slug="contribucion").first()
        first_slot, second_slot = AppointmentSlot.query.order_by(AppointmentSlot.start_time).all()

    created = envelope(client.post("/api/v1/public/appointments", json=booking_payload(tribute.id, first_slot.id)), 201)
    appointments = envelope(client.get("/api/v1/admin/appointments?search=Persona"), 200)
    appointment_id = appointments["items"][0]["id"]
    envelope(client.patch(f"/api/v1/admin/appointments/{appointment_id}", json={"internal_notes": "Reviewed"}), 200)
    moved = envelope(client.post(f"/api/v1/admin/appointments/{appointment_id}/reschedule", json={"slot_id": second_slot.id}), 200)
    assert moved["slot_id"] == second_slot.id
    envelope(client.post(f"/api/v1/admin/appointments/{appointment_id}/cancel"), 200)
    reactivation = client.patch(f"/api/v1/admin/appointments/{appointment_id}", json={"status": "reserved"})
    assert reactivation.status_code == 400
    assert reactivation.json["error"]["code"] == "invalid_transition"

    new_tribute = envelope(client.post("/api/v1/admin/tribute-types", json={"name": "Patente", "slug": "patente"}), 201)
    envelope(client.patch(f"/api/v1/admin/tribute-types/{new_tribute['id']}", json={"is_active": False}), 200)
    envelope(client.delete(f"/api/v1/admin/tribute-types/{new_tribute['id']}"), 200)
    new_location = envelope(client.post("/api/v1/admin/locations", json={"name": "Anexo", "is_active": True}), 201)
    envelope(client.patch(f"/api/v1/admin/locations/{new_location['id']}", json={"is_active": False}), 200)
    envelope(client.delete(f"/api/v1/admin/locations/{new_location['id']}"), 200)
    preserved_location = envelope(client.delete(f"/api/v1/admin/locations/{moved['location_id']}"), 200)
    assert preserved_location["soft_deleted"] is True

    rule = envelope(client.post("/api/v1/admin/availability/rules", json={
        "name": "Rule", "start_date": (date.today() + timedelta(days=5)).isoformat(), "end_date": (date.today() + timedelta(days=5)).isoformat(),
        "weekdays": [(date.today() + timedelta(days=5)).weekday()], "start_time": "14:00", "end_time": "15:00",
        "slot_duration_minutes": 30, "capacity_per_slot": 1, "applies_to_all": True,
    }), 201)
    invalid_rule = client.post("/api/v1/admin/availability/rules", json={
        "name": "Invalid", "start_date": (date.today() + timedelta(days=5)).isoformat(), "end_date": (date.today() + timedelta(days=5)).isoformat(),
        "weekdays": [0], "start_time": "14:00", "end_time": "15:00", "applies_to_all": False, "tribute_type_ids": [999999],
    })
    assert invalid_rule.status_code == 400
    assert invalid_rule.json["error"]["code"] == "invalid_tributes"
    envelope(client.post(f"/api/v1/admin/availability/rules/{rule['id']}/generate-slots"), 200)
    holiday = envelope(client.post("/api/v1/admin/availability/holidays", json={"date": (date.today() + timedelta(days=10)).isoformat()}), 201)
    envelope(client.get("/api/v1/admin/availability/holidays"), 200)
    envelope(client.delete(f"/api/v1/admin/availability/holidays/{holiday['id']}"), 200)

    user = envelope(client.post("/api/v1/admin/access/users", json={
        "username": "inactive", "email": "inactive@example.test", "password": "another-safe-password", "is_active": False,
    }), 201)
    assert user["is_active"] is False
    envelope(client.patch(f"/api/v1/admin/access/users/{user['id']}/password", json={"password": "changed-safe-password"}), 200)
    envelope(client.delete(f"/api/v1/admin/access/users/{user['id']}"), 200)
    envelope(client.get("/api/v1/admin/dashboard"), 200)
    envelope(client.get("/api/v1/admin/access/activity-logs"), 200)
    csv = client.get("/api/v1/admin/access/activity-logs.csv")
    assert csv.status_code == 200
    assert csv.content_type.startswith("text/csv")


def test_regular_admin_cannot_access_superuser_resources(app, monkeypatch):
    client = admin_client(app, monkeypatch, email="operator@example.test")
    envelope(client.get("/api/v1/admin/dashboard"), 200)
    denied = client.get("/api/v1/admin/access/users")
    assert denied.status_code == 403
    assert denied.content_type.startswith("application/json")
    assert denied.json["error"]["code"] == "superuser_required"
