"""Public API endpoints for the citizen booking wizard."""

from __future__ import annotations

from datetime import date, datetime

from flask import jsonify, request
from marshmallow import ValidationError

from app.extensions import db
from app.models.appointment import Appointment
from app.models.availability import AppointmentSlot, HolidayOrBlockedDay, Location
from app.models.tribute_type import TributeType
from app.schemas.appointment_schema import AppointmentCreateSchema
from app.schemas.tribute_type_schema import TributeTypeSchema
from app.services import appointment_service
from app.services.availability_service import (
    list_available_dates,
    list_available_slots,
)
from app.utils.responses import fail, ok, paginated
from . import public_bp


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------

@public_bp.get("/tribute-types")
def list_tribute_types():
    items = (
        TributeType.query.filter_by(is_active=True)
        .order_by(TributeType.sort_order.asc(), TributeType.name.asc())
        .all()
    )
    return ok([TributeTypeSchema().dump(t) for t in items])


@public_bp.get("/tribute-types/<int:tribute_id>")
def get_tribute_type(tribute_id: int):
    t = db.session.get(TributeType, tribute_id)
    if not t or not t.is_active:
        return fail("Tributo no encontrado", 404, code="not_found")
    return ok(TributeTypeSchema().dump(t))


@public_bp.get("/locations")
def list_locations():
    rows = Location.query.filter_by(is_active=True).order_by(Location.name.asc()).all()
    return ok([loc.to_dict() for loc in rows])


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

@public_bp.get("/availability")
def availability_overview():
    """Return list of available dates for a tribute type."""
    try:
        tribute_id = int(request.args.get("tribute_type_id", 0))
    except ValueError:
        return fail("tribute_type_id inválido", 400, code="bad_request")
    if not tribute_id:
        return fail("tribute_type_id es requerido", 400, code="missing_param")

    tribute = db.session.get(TributeType, tribute_id)
    if not tribute or not tribute.is_active:
        return fail("Tributo no disponible", 404, code="not_found")

    try:
        from_date = _parse_date(request.args.get("from"), default=date.today())
        days = int(request.args.get("days", 30))
    except ValueError as exc:
        return fail(str(exc), 400, code="bad_request")
    if days < 1 or days > 90:
        return fail("days debe estar entre 1 y 90", 400, code="bad_request")

    to_date = _add_days(from_date, days)
    dates = list_available_dates(tribute_id, from_date=from_date, to_date=to_date)
    return ok({
        "tribute_type_id": tribute_id,
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "dates": dates,
    })


@public_bp.get("/slots")
def list_slots():
    """Return slots for a specific date + tribute type."""
    try:
        tribute_id = int(request.args.get("tribute_type_id", 0))
        date_str = request.args.get("date", "")
    except ValueError:
        return fail("Parámetros inválidos", 400, code="bad_request")
    if not tribute_id or not date_str:
        return fail("tribute_type_id y date son requeridos", 400, code="missing_param")

    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return fail("Formato de fecha inválido (YYYY-MM-DD)", 400, code="bad_request")

    if target < date.today():
        return fail("No puede reservar turnos en fechas pasadas", 400, code="invalid_date")

    slots = list_available_slots(tribute_id, target)
    blocked = HolidayOrBlockedDay.query.filter_by(date=target).first()
    return ok({
        "date": target.isoformat(),
        "tribute_type_id": tribute_id,
        "is_blocked": blocked is not None,
        "block_reason": (blocked.reason if blocked else "") or "",
        "slots": slots,
    })


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------

@public_bp.post("/appointments")
def create_appointment():
    payload = request.get_json(silent=True) or {}
    try:
        data = AppointmentCreateSchema().load(payload)
    except ValidationError as err:
        return fail("Datos inválidos", 422, code="validation_error", errors=err.messages)

    try:
        appointment = appointment_service.book_appointment(data)
    except appointment_service.BookingError as exc:
        return fail(exc.message, exc.http_status, code=exc.code)

    email_delivery = "not_requested"
    if appointment.email:
        from app.services.email_service import send_reservation_confirmed_email
        email_delivery = "sent" if send_reservation_confirmed_email(appointment) else "failed"

    response = appointment.to_public_dict()
    response["email_delivery"] = email_delivery
    return ok(response, status=201)


@public_bp.get("/appointments/<string:code>")
def get_appointment_by_code(code: str):
    """Look up a reservation by its friendly code (no auth, citizen-facing)."""
    appt = Appointment.query.filter_by(reservation_code=code.strip().upper()).first()
    if not appt:
        return fail("No se encontró la reserva", 404, code="not_found")

    return ok(appt.to_public_dict())


@public_bp.post("/appointments/<string:code>/cancel")
def cancel_appointment_public(code: str):
    document = appointment_service.normalize_document(
        request.args.get("document") or (request.json or {}).get("document")
    )
    if not document:
        return fail("document es requerido para cancelar una reserva", 400, code="missing_document")

    appt = Appointment.query.filter_by(reservation_code=code.strip().upper()).first()
    if not appt:
        return fail("No se encontró la reserva", 404, code="not_found")
    stored_document = appointment_service.normalize_document(appt.citizen_document or "")
    if stored_document != document:
        return fail("Los datos no coinciden con la reserva", 404, code="not_found")

    if appt.status not in ("reserved", "confirmed"):
        return fail("La reserva no puede cancelarse en su estado actual", 400, code="invalid_state")

    appointment_service.cancel_appointment(appt, by_admin=False)
    return ok({"cancelled": True, "reservation_code": appt.reservation_code})


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _parse_date(value: str | None, *, default: date) -> date:
    if not value:
        return default
    return datetime.strptime(value, "%Y-%m-%d").date()


def _add_days(value: date, days: int) -> date:
    from datetime import timedelta
    return value + timedelta(days=days)
