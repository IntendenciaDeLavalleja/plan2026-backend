"""Appointment booking service: transactional overbooking protection."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.appointment import Appointment
from app.models.availability import AppointmentSlot, HolidayOrBlockedDay
from app.models.tribute_type import TributeType
from app.models.setting import SystemSetting
from app.services.reservation_code_service import generate_reservation_code
from app.services.availability_service import is_date_blocked


class BookingError(Exception):
    """Raised when a booking cannot be made."""

    def __init__(self, code: str, message: str, http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _max_per_document() -> int:
    try:
        return int(SystemSetting.get("max_reservations_per_document", 1))
    except (TypeError, ValueError):
        return 1


def _anticipation_min_hours() -> int:
    try:
        return int(SystemSetting.get("min_anticipation_hours", 1))
    except (TypeError, ValueError):
        return 1


def _anticipation_max_days() -> int:
    try:
        return int(SystemSetting.get("max_anticipation_days", 90))
    except (TypeError, ValueError):
        return 90


def _count_active_for_document(document: str) -> int:
    return Appointment.query.filter(
        Appointment.citizen_document == document,
        Appointment.status.in_(("reserved", "confirmed")),
    ).count()


def book_appointment(payload: dict) -> Appointment:
    """Create a new appointment transactionally with overbooking protection.

    `payload` keys:
        - tribute_type_id (int)
        - slot_id (int)
        - citizen_name, citizen_document, phone, email, reference_value, comments
        - accept_terms (bool)
    """
    tribute_type_id: int = payload["tribute_type_id"]
    slot_id: int = payload["slot_id"]
    document: str = (payload["citizen_document"] or "").strip()

    tribute = db.session.get(TributeType, tribute_type_id)
    if not tribute or not tribute.is_active:
        raise BookingError("tribute_inactive", "El tributo seleccionado no está disponible", 400)

    if tribute.requires_padron and not (payload.get("reference_value") or "").strip():
        raise BookingError("padron_required", "Este trámite requiere un padrón / código municipal", 400)
    if tribute.requires_matricula and not (payload.get("reference_value") or "").strip():
        raise BookingError("matricula_required", "Este trámite requiere una matrícula", 400)

    # Lock the slot row to avoid race conditions
    slot: Optional[AppointmentSlot] = db.session.execute(
        select(AppointmentSlot).where(AppointmentSlot.id == slot_id).with_for_update()
    ).scalar_one_or_none()

    if slot is None:
        raise BookingError("slot_not_found", "El turno seleccionado no existe", 404)
    if slot.is_blocked:
        raise BookingError("slot_blocked", "El turno seleccionado no se encuentra disponible", 400)
    if slot.tribute_type_id and slot.tribute_type_id != tribute_type_id:
        raise BookingError("slot_tribute_mismatch", "El turno no corresponde al tributo seleccionado", 400)

    if slot.date and is_date_blocked(slot.date):
        raise BookingError("date_blocked", "La fecha seleccionada no está disponible", 400)

    slot_start_dt = datetime.combine(slot.date, slot.start_time) if slot.date and slot.start_time else None
    if slot_start_dt is not None:
        now = datetime.now()
        delta_hours = (slot_start_dt - now).total_seconds() / 3600
        if delta_hours < _anticipation_min_hours():
            raise BookingError(
                "too_soon",
                f"Debe reservar con al menos {_anticipation_min_hours()} hora(s) de anticipación",
                400,
            )
        if delta_hours > _anticipation_max_days() * 24:
            raise BookingError("too_far", "La fecha seleccionada excede la anticipación máxima permitida", 400)

    if slot.reserved_count >= slot.capacity:
        raise BookingError("slot_full", "Lo sentimos, este turno acaba de agotarse", 409)

    max_per_doc = _max_per_document()
    if max_per_doc > 0 and _count_active_for_document(document) >= max_per_doc:
        raise BookingError(
            "max_per_document",
            f"Ya tiene reservas activas. Límite permitido: {max_per_doc}",
            409,
        )

    # Atomic increment
    slot.reserved_count = (slot.reserved_count or 0) + 1

    appointment = Appointment(
        reservation_code=generate_reservation_code(),
        tribute_type_id=tribute_type_id,
        location_id=slot.location_id,
        slot_id=slot.id,
        citizen_name=payload["citizen_name"].strip(),
        citizen_document=document,
        phone=payload["phone"].strip(),
        email=(payload.get("email") or None),
        reference_value=(payload.get("reference_value") or None),
        comments=(payload.get("comments") or None),
        status="reserved",
    )

    try:
        db.session.add(appointment)
        db.session.flush()  # surface DB errors before we commit
    except IntegrityError as exc:  # pragma: no cover
        db.session.rollback()
        raise BookingError("db_error", "No se pudo registrar la reserva", 500) from exc

    # If we got here, the increment has not been committed. Commit both atomically.
    try:
        db.session.commit()
    except IntegrityError as exc:  # pragma: no cover - duplicate code race
        db.session.rollback()
        raise BookingError("duplicate_code", "Conflicto al generar el código, intente nuevamente", 500) from exc
    except Exception as exc:  # pragma: no cover
        db.session.rollback()
        raise BookingError("db_error", "Error al registrar la reserva", 500) from exc

    return appointment


def cancel_appointment(appointment: Appointment, *, by_admin: bool = False) -> None:
    """Release the slot and mark the appointment as cancelled."""
    if appointment.status == "cancelled":
        return
    appointment.status = "cancelled"
    appointment.cancelled_at = datetime.utcnow()
    slot = appointment.slot
    if slot is not None:
        slot.reserved_count = max(0, (slot.reserved_count or 0) - 1)
    db.session.commit()
