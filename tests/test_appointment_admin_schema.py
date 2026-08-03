from datetime import date, time
from types import SimpleNamespace

from app.schemas.appointment_schema import AppointmentAdminSchema


def test_admin_schema_reads_date_and_time_from_appointment_slot():
    appointment = SimpleNamespace(
        id=1,
        reservation_code="IDL-AF-2026-TEST01",
        status="reserved",
        tribute_type_id=1,
        location_id=1,
        slot_id=99,
        citizen_name="Persona Demo",
        citizen_document="1.234.567-8",
        phone="099123456",
        email="persona@example.com",
        reference_value="12345",
        comments=None,
        internal_notes=None,
        created_at=None,
        updated_at=None,
        cancelled_at=None,
        slot=SimpleNamespace(date=date(2026, 8, 3), start_time=time(10, 0), end_time=time(11, 0)),
    )

    data = AppointmentAdminSchema().dump(appointment)

    assert data["date"] == "2026-08-03"
    assert data["start_time"] == "10:00"
    assert data["end_time"] == "11:00"


def test_admin_schema_keeps_missing_slot_schedule_empty():
    appointment = SimpleNamespace(slot=None)

    data = AppointmentAdminSchema().dump(appointment)

    assert data["date"] is None
    assert data["start_time"] is None
    assert data["end_time"] is None
