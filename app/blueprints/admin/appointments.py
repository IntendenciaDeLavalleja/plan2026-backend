"""Admin appointments management."""

from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, request
from flask_login import login_required
from marshmallow import ValidationError
from sqlalchemy import or_

from app.extensions import db
from app.models.appointment import Appointment, APPOINTMENT_STATUSES
from app.models.availability import AppointmentSlot
from app.models.tribute_type import TributeType
from app.schemas.appointment_schema import (
    AppointmentAdminSchema,
    AppointmentAdminUpdateSchema,
)
from app.services import appointment_service
from app.services.email_service import send_reservation_confirmed_email
from app.utils.logging_helper import log_activity
from app.utils.responses import fail, ok, paginated

admin_appointments_bp = Blueprint("admin_appointments", __name__)


@admin_appointments_bp.get("")
@login_required
def list_appointments():
    page = int(request.args.get("page", 1) or 1)
    per_page = min(int(request.args.get("per_page", 30) or 30), 200)
    q = (
        Appointment.query
        .join(AppointmentSlot, Appointment.slot_id == AppointmentSlot.id)
    )

    if request.args.get("status"):
        q = q.filter(Appointment.status == request.args["status"])
    if request.args.get("tribute_type_id"):
        q = q.filter(Appointment.tribute_type_id == int(request.args["tribute_type_id"]))
    if request.args.get("from"):
        try:
            q = q.filter(AppointmentSlot.date >= datetime.strptime(request.args["from"], "%Y-%m-%d").date())
        except ValueError:
            pass
    if request.args.get("to"):
        try:
            q = q.filter(AppointmentSlot.date <= datetime.strptime(request.args["to"], "%Y-%m-%d").date())
        except ValueError:
            pass
    if request.args.get("code"):
        q = q.filter(Appointment.reservation_code.ilike(f"%{request.args['code'].strip()}%"))
    if request.args.get("search"):
        term = f"%{request.args['search'].strip()}%"
        q = q.filter(or_(
            Appointment.citizen_name.ilike(term),
            Appointment.citizen_document.ilike(term),
            Appointment.email.ilike(term),
            Appointment.reservation_code.ilike(term),
        ))

    total = q.count()
    rows = (
        q.order_by(AppointmentSlot.date.desc(), AppointmentSlot.start_time.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return ok(paginated([AppointmentAdminSchema().dump(r) for r in rows], page, per_page, total))


@admin_appointments_bp.get("/<int:appointment_id>")
@login_required
def get_appointment(appointment_id: int):
    a = db.session.get(Appointment, appointment_id)
    if not a:
        return fail("Reserva no encontrada", 404, code="not_found")
    return ok(AppointmentAdminSchema().dump(a))


@admin_appointments_bp.patch("/<int:appointment_id>")
@login_required
def update_appointment(appointment_id: int):
    a = db.session.get(Appointment, appointment_id)
    if not a:
        return fail("Reserva no encontrada", 404, code="not_found")
    try:
        data = AppointmentAdminUpdateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return fail("Datos inválidos", 422, code="validation_error", errors=err.messages)

    if "status" in data and data["status"] != a.status:
        new_status = data["status"]
        if new_status == "cancelled" and a.status != "cancelled":
            appointment_service.cancel_appointment(a, by_admin=True)
        else:
            a.status = new_status
    if "internal_notes" in data:
        a.internal_notes = data["internal_notes"]
    if data.get("slot_id") and data["slot_id"] != a.slot_id:
        new_slot = db.session.get(AppointmentSlot, data["slot_id"])
        if not new_slot:
            return fail("Slot destino no encontrado", 404, code="slot_not_found")
        if new_slot.is_blocked or new_slot.reserved_count >= new_slot.capacity:
            return fail("El slot destino no tiene cupo", 400, code="slot_unavailable")
        old_slot = a.slot
        if old_slot:
            old_slot.reserved_count = max(0, old_slot.reserved_count - 1)
        new_slot.reserved_count += 1
        a.slot = new_slot
    db.session.commit()
    log_activity("APPOINTMENT_UPDATE", f"Reserva {a.reservation_code} actualizada")
    return ok(AppointmentAdminSchema().dump(a))


@admin_appointments_bp.post("/<int:appointment_id>/cancel")
@login_required
def cancel_appointment(appointment_id: int):
    a = db.session.get(Appointment, appointment_id)
    if not a:
        return fail("Reserva no encontrada", 404, code="not_found")
    if a.status == "cancelled":
        return ok(AppointmentAdminSchema().dump(a))
    appointment_service.cancel_appointment(a, by_admin=True)
    log_activity("APPOINTMENT_CANCEL", f"Reserva {a.reservation_code} cancelada por admin")
    return ok(AppointmentAdminSchema().dump(a))


@admin_appointments_bp.post("/<int:appointment_id>/reschedule")
@login_required
def reschedule_appointment(appointment_id: int):
    a = db.session.get(Appointment, appointment_id)
    if not a:
        return fail("Reserva no encontrada", 404, code="not_found")
    if a.status not in ("reserved", "confirmed"):
        return fail("La reserva no puede reprogramarse en su estado actual", 400, code="invalid_state")

    body = request.get_json(silent=True) or {}
    try:
        new_slot_id = int(body["slot_id"])
    except (KeyError, TypeError, ValueError):
        return fail("slot_id es requerido", 400, code="missing_slot")
    new_slot = db.session.get(AppointmentSlot, new_slot_id)
    if not new_slot:
        return fail("Slot destino no encontrado", 404, code="slot_not_found")
    if new_slot.is_blocked:
        return fail("El slot destino está bloqueado", 400, code="slot_blocked")
    if new_slot.reserved_count >= new_slot.capacity:
        return fail("El slot destino no tiene cupo", 400, code="slot_full")

    old_slot = a.slot
    if old_slot and old_slot.id != new_slot.id:
        old_slot.reserved_count = max(0, old_slot.reserved_count - 1)
    new_slot.reserved_count += 1
    a.slot = new_slot
    if new_slot.location_id:
        a.location_id = new_slot.location_id
    if new_slot.tribute_type_id:
        a.tribute_type_id = new_slot.tribute_type_id
    db.session.commit()
    log_activity("APPOINTMENT_RESCHEDULE", f"Reserva {a.reservation_code} reprogramada a slot {new_slot.id}")
    return ok(AppointmentAdminSchema().dump(a))


@admin_appointments_bp.get("/status-options")
@login_required
def status_options():
    return ok([{"value": s, "label": s.replace("_", " ").capitalize()} for s in APPOINTMENT_STATUSES])
