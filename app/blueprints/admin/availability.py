"""Admin availability + slots management."""

from __future__ import annotations

from datetime import date, datetime, time

from flask import Blueprint, request
from flask_login import login_required
from marshmallow import ValidationError
from sqlalchemy import func

from app.extensions import db
from app.models.appointment import Appointment
from app.models.availability import (
    AppointmentSlot,
    AvailabilityRule,
    HolidayOrBlockedDay,
    Location,
)
from app.models.tribute_type import TributeType
from app.schemas.availability_schema import (
    AppointmentSlotSchema,
    AvailabilityRuleCreateSchema,
    AvailabilityRuleSchema,
    HolidaySchema,
    LocationCreateSchema,
    LocationSchema,
)
from app.services.availability_service import (
    bulk_generate_slots,
    generate_slots_for_rule,
)
from app.utils.logging_helper import log_activity
from app.utils.responses import fail, ok, paginated

admin_availability_bp = Blueprint("admin_availability", __name__)

# Re-export the locations blueprint for convenience
from .locations import admin_locations_bp  # noqa: E402


# ---------------------------------------------------------------------------
# Availability rules
# ---------------------------------------------------------------------------

@admin_availability_bp.get("/rules")
@login_required
def list_rules():
    page = int(request.args.get("page", 1) or 1)
    per_page = min(int(request.args.get("per_page", 50) or 50), 200)
    query = AvailabilityRule.query.order_by(AvailabilityRule.start_date.desc())
    total = query.count()
    rows = query.offset((page - 1) * per_page).limit(per_page).all()
    return ok(paginated([AvailabilityRuleSchema().dump(r) for r in rows], page, per_page, total))


@admin_availability_bp.post("/rules")
@login_required
def create_rule():
    try:
        data = AvailabilityRuleCreateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return fail("Datos inválidos", 422, code="validation_error", errors=err.messages)

    rule = AvailabilityRule(
        name=data["name"],
        start_date=data["start_date"],
        end_date=data["end_date"],
        weekdays=data["weekdays"],
        start_time=data["start_time"],
        end_time=data["end_time"],
        slot_duration_minutes=data["slot_duration_minutes"],
        capacity_per_slot=data["capacity_per_slot"],
        location_id=data.get("location_id"),
        team=data.get("team"),
        applies_to_all=data["applies_to_all"],
        is_active=data["is_active"],
    )
    if not rule.applies_to_all:
        ids = data.get("tribute_type_ids") or []
        if not ids:
            return fail("Seleccione al menos un tributo o marque 'aplica a todos'", 400, code="missing_tributes")
        tributes = TributeType.query.filter(TributeType.id.in_(ids), TributeType.is_active.is_(True)).all()
        if len(tributes) != len(set(ids)):
            return fail("Uno o más tributos no están disponibles", 400, code="invalid_tributes")
        rule.tribute_types = tributes
    db.session.add(rule)
    db.session.commit()
    log_activity("RULE_CREATE", f"Regla creada: {rule.name}")
    return ok(AvailabilityRuleSchema().dump(rule), status=201)


@admin_availability_bp.get("/rules/<int:rule_id>")
@login_required
def get_rule(rule_id: int):
    rule = db.session.get(AvailabilityRule, rule_id)
    if not rule:
        return fail("Regla no encontrada", 404, code="not_found")
    return ok(AvailabilityRuleSchema().dump(rule))


@admin_availability_bp.patch("/rules/<int:rule_id>")
@login_required
def update_rule(rule_id: int):
    rule = db.session.get(AvailabilityRule, rule_id)
    if not rule:
        return fail("Regla no encontrada", 404, code="not_found")
    try:
        data = AvailabilityRuleCreateSchema().load(request.get_json(silent=True) or {}, partial=True)
    except ValidationError as err:
        return fail("Datos inválidos", 422, code="validation_error", errors=err.messages)

    for key, value in data.items():
        if key != "tribute_type_ids":
            setattr(rule, key, value)
    if "tribute_type_ids" in data or "applies_to_all" in data:
        ids = data.get("tribute_type_ids", [tribute.id for tribute in rule.tribute_types])
        if rule.applies_to_all:
            rule.tribute_types = []
        else:
            if not ids:
                return fail("Seleccione al menos un tributo o marque 'aplica a todos'", 400, code="missing_tributes")
            tributes = TributeType.query.filter(TributeType.id.in_(ids), TributeType.is_active.is_(True)).all()
            if len(tributes) != len(set(ids)):
                return fail("Uno o más tributos no están disponibles", 400, code="invalid_tributes")
            rule.tribute_types = tributes
    db.session.commit()
    log_activity("RULE_UPDATE", f"Regla actualizada: {rule.name}")
    return ok(AvailabilityRuleSchema().dump(rule))


@admin_availability_bp.delete("/rules/<int:rule_id>")
@login_required
def delete_rule(rule_id: int):
    rule = db.session.get(AvailabilityRule, rule_id)
    if not rule:
        return fail("Regla no encontrada", 404, code="not_found")
    db.session.delete(rule)
    db.session.commit()
    log_activity("RULE_DELETE", f"Regla eliminada: {rule.name}")
    return ok({"deleted": True, "id": rule_id})


@admin_availability_bp.post("/rules/<int:rule_id>/generate-slots")
@login_required
def trigger_generate_slots(rule_id: int):
    rule = db.session.get(AvailabilityRule, rule_id)
    if not rule:
        return fail("Regla no encontrada", 404, code="not_found")
    overwrite = (request.args.get("overwrite", "false").lower() in {"1", "true", "yes"})
    created = generate_slots_for_rule(rule, overwrite=overwrite)
    log_activity("RULE_GENERATE", f"Regla {rule.name} generó {created} slots")
    return ok({"created_slots": created})


# ---------------------------------------------------------------------------
# Slot ad-hoc generation (no rule needed)
# ---------------------------------------------------------------------------

@admin_availability_bp.post("/slots/bulk-generate")
@login_required
def admin_bulk_generate_slots():
    body = request.get_json(silent=True) or {}
    try:
        start_date = datetime.strptime(body["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(body["end_date"], "%Y-%m-%d").date()
        start_time = datetime.strptime(body["start_time"], "%H:%M").time()
        end_time = datetime.strptime(body["end_time"], "%H:%M").time()
        duration = int(body.get("slot_duration_minutes", 20))
        capacity = int(body.get("capacity_per_slot", 1))
    except (KeyError, ValueError, TypeError):
        return fail("Datos inválidos para generación de slots", 400, code="bad_request")

    if end_date < start_date:
        return fail("end_date debe ser >= start_date", 400, code="bad_request")
    if end_time <= start_time:
        return fail("end_time debe ser > start_time", 400, code="bad_request")

    weekdays = body.get("weekdays") or [0, 1, 2, 3, 4]
    tribute_type_ids = body.get("tribute_type_ids")
    applies_to_all = bool(body.get("applies_to_all", False))
    overwrite = bool(body.get("overwrite", False))
    location_id = body.get("location_id")

    created = bulk_generate_slots(
        start_date=start_date,
        end_date=end_date,
        weekdays=weekdays,
        start_time=start_time,
        end_time=end_time,
        duration_minutes=duration,
        capacity=capacity,
        location_id=location_id,
        tribute_type_ids=tribute_type_ids,
        applies_to_all=applies_to_all,
        overwrite=overwrite,
    )
    log_activity("SLOTS_BULK", f"Generados {created} slots")
    return ok({"created_slots": created})


# ---------------------------------------------------------------------------
# Slots listing / patching
# ---------------------------------------------------------------------------

@admin_availability_bp.get("/slots")
@login_required
def list_slots():
    page = int(request.args.get("page", 1) or 1)
    per_page = min(int(request.args.get("per_page", 50) or 50), 200)
    q = AppointmentSlot.query
    if request.args.get("tribute_type_id"):
        q = q.filter(AppointmentSlot.tribute_type_id == int(request.args.get("tribute_type_id")))
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
    if request.args.get("only_blocked") in {"1", "true", "yes"}:
        q = q.filter(AppointmentSlot.is_blocked.is_(True))

    total = q.count()
    rows = (
        q.order_by(AppointmentSlot.date.asc(), AppointmentSlot.start_time.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return ok(paginated([AppointmentSlotSchema().dump(r) for r in rows], page, per_page, total))


@admin_availability_bp.patch("/slots/<int:slot_id>")
@login_required
def update_slot(slot_id: int):
    slot = db.session.get(AppointmentSlot, slot_id)
    if not slot:
        return fail("Slot no encontrado", 404, code="not_found")
    body = request.get_json(silent=True) or {}
    if "capacity" in body:
        try:
            new_cap = int(body["capacity"])
        except (TypeError, ValueError):
            return fail("capacity inválido", 400, code="bad_request")
        if new_cap < slot.reserved_count:
            return fail("La capacidad no puede ser menor a las reservas actuales", 400, code="capacity_too_low")
        slot.capacity = new_cap
    if "is_blocked" in body:
        slot.is_blocked = bool(body["is_blocked"])
    if "block_reason" in body:
        slot.block_reason = body.get("block_reason") or None
    if "notes" in body:
        slot.notes = body.get("notes") or None
    if "tribute_type_id" in body:
        try:
            slot.tribute_type_id = int(body["tribute_type_id"]) if body["tribute_type_id"] else None
        except (TypeError, ValueError):
            return fail("tribute_type_id inválido", 400, code="bad_request")
    if "location_id" in body:
        try:
            slot.location_id = int(body["location_id"]) if body["location_id"] else None
        except (TypeError, ValueError):
            return fail("location_id inválido", 400, code="bad_request")

    db.session.commit()
    log_activity("SLOT_UPDATE", f"Slot #{slot.id} actualizado")
    return ok(AppointmentSlotSchema().dump(slot))


@admin_availability_bp.delete("/slots/<int:slot_id>")
@login_required
def delete_slot(slot_id: int):
    slot = db.session.get(AppointmentSlot, slot_id)
    if not slot:
        return fail("Slot no encontrado", 404, code="not_found")
    if slot.reserved_count > 0:
        return fail("No se puede eliminar un slot con reservas activas", 400, code="slot_has_bookings")
    db.session.delete(slot)
    db.session.commit()
    log_activity("SLOT_DELETE", f"Slot #{slot_id} eliminado")
    return ok({"deleted": True, "id": slot_id})


ACTIVE_APPOINTMENT_STATUSES = ("reserved", "confirmed", "called", "in_service")

@admin_availability_bp.post("/slots/bulk-delete")
@login_required
def bulk_delete_slots():
    """Elimina horarios en lote segun filtros.

    Con ``confirm`` distinto de ``True`` devuelve una vista previa y no borra nada.
    Con ``confirm: true`` cancela los turnos activos vinculados y elimina los slots.
    """
    body = request.get_json(silent=True) or {}

    def _parse_date(key):
        raw = (body.get(key) or "").strip() if isinstance(body.get(key), str) else body.get(key)
        if not raw:
            return None
        try:
            return datetime.strptime(str(raw), "%Y-%m-%d").date()
        except (TypeError, ValueError):
            raise ValueError(key)

    try:
        date_from = _parse_date("from")
        date_to = _parse_date("to")
    except ValueError as err:
        return fail(
            f"Fecha invalida en '{err.args[0]}'. Formato esperado AAAA-MM-DD.",
            400,
            code="invalid_date",
        )

    tribute_type_id = body.get("tribute_type_id") or None
    location_id = body.get("location_id") or None
    only_blocked = bool(body.get("only_blocked"))

    if not any([date_from, date_to, tribute_type_id, location_id, only_blocked]):
        return fail(
            "Indica al menos un filtro. Este endpoint no borra la agenda completa.",
            400,
            code="filters_required",
        )
    if date_from and date_to and date_from > date_to:
        return fail("La fecha 'desde' no puede ser posterior a 'hasta'", 400, code="invalid_range")

    q = AppointmentSlot.query
    if date_from:
        q = q.filter(AppointmentSlot.date >= date_from)
    if date_to:
        q = q.filter(AppointmentSlot.date <= date_to)
    if tribute_type_id:
        try:
            q = q.filter(AppointmentSlot.tribute_type_id == int(tribute_type_id))
        except (TypeError, ValueError):
            return fail("tribute_type_id invalido", 400, code="bad_request")
    if location_id:
        try:
            q = q.filter(AppointmentSlot.location_id == int(location_id))
        except (TypeError, ValueError):
            return fail("location_id invalido", 400, code="bad_request")
    if only_blocked:
        q = q.filter(AppointmentSlot.is_blocked.is_(True))

    slot_ids = [row[0] for row in q.with_entities(AppointmentSlot.id).all()]

    if not slot_ids:
        return ok({
            "preview": body.get("confirm") is not True,
            "slots": 0,
            "deleted_slots": 0,
            "appointments_total": 0,
            "appointments_active": 0,
            "cancelled_appointments": 0,
            "dates": [],
            "codes": [],
        })

    dates = [
        {"date": row[0].isoformat(), "slots": int(row[1])}
        for row in (
            q.with_entities(AppointmentSlot.date, func.count(AppointmentSlot.id))
            .group_by(AppointmentSlot.date)
            .order_by(AppointmentSlot.date.asc())
            .all()
        )
    ]

    linked = Appointment.query.filter(Appointment.slot_id.in_(slot_ids))
    active = linked.filter(Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES))
    appointments_total = linked.count()
    appointments_active = active.count()
    codes = [
        row[0]
        for row in active.with_entities(Appointment.reservation_code)
        .order_by(Appointment.id.asc())
        .limit(200)
        .all()
    ]

    if body.get("confirm") is not True:
        return ok({
            "preview": True,
            "slots": len(slot_ids),
            "appointments_total": appointments_total,
            "appointments_active": appointments_active,
            "dates": dates,
            "codes": codes,
        })

    chunk_size = 500
    cancelled = 0
    for start in range(0, len(slot_ids), chunk_size):
        chunk = slot_ids[start:start + chunk_size]
        cancelled += (
            Appointment.query
            .filter(Appointment.slot_id.in_(chunk))
            .filter(Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES))
            .update(
                {Appointment.status: "cancelled", Appointment.cancelled_at: db.func.now()},
                synchronize_session=False,
            )
        )
        AppointmentSlot.query.filter(AppointmentSlot.id.in_(chunk)).delete(synchronize_session=False)
    db.session.commit()

    log_activity(
        "SLOTS_BULK_DELETE",
        (
            f"Borrado en lote: {len(slot_ids)} horarios eliminados, {cancelled} turnos cancelados. "
            f"Filtros: from={date_from} to={date_to} tribute_type_id={tribute_type_id} "
            f"location_id={location_id} only_blocked={only_blocked}"
        ),
    )

    return ok({
        "preview": False,
        "deleted_slots": len(slot_ids),
        "appointments_total": appointments_total,
        "cancelled_appointments": cancelled,
        "dates": dates,
        "codes": codes,
    })


@admin_availability_bp.post("/slots/block")
@login_required
def block_slots():
    body = request.get_json(silent=True) or {}
    try:
        target_date = datetime.strptime(body["date"], "%Y-%m-%d").date()
    except (KeyError, ValueError, TypeError):
        return fail("Debe indicar la fecha", 400, code="missing_date")

    q = AppointmentSlot.query.filter(AppointmentSlot.date == target_date)
    if body.get("tribute_type_id"):
        q = q.filter(AppointmentSlot.tribute_type_id == int(body["tribute_type_id"]))
    slots = q.all()
    for s in slots:
        s.is_blocked = True
        s.block_reason = body.get("reason") or s.block_reason
    db.session.commit()
    log_activity("SLOT_BLOCK", f"Bloqueados {len(slots)} slots del {target_date.isoformat()}")
    return ok({"blocked": len(slots)})


# ---------------------------------------------------------------------------
# Holidays
# ---------------------------------------------------------------------------

@admin_availability_bp.get("/holidays")
@login_required
def list_holidays():
    rows = HolidayOrBlockedDay.query.order_by(HolidayOrBlockedDay.date.asc()).all()
    return ok([HolidaySchema().dump(r) for r in rows])


@admin_availability_bp.post("/holidays")
@login_required
def create_holiday():
    try:
        data = HolidaySchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return fail("Datos inválidos", 422, code="validation_error", errors=err.messages)
    if HolidayOrBlockedDay.query.filter_by(date=data["date"]).first():
        return fail("Ya existe un día no laborable para esa fecha", 409, code="holiday_exists")
    h = HolidayOrBlockedDay(**data)
    db.session.add(h)
    db.session.commit()
    log_activity("HOLIDAY_CREATE", f"Feriado creado: {h.date.isoformat()}")
    return ok(HolidaySchema().dump(h), status=201)


@admin_availability_bp.delete("/holidays/<int:holiday_id>")
@login_required
def delete_holiday(holiday_id: int):
    h = db.session.get(HolidayOrBlockedDay, holiday_id)
    if not h:
        return fail("Feriado no encontrado", 404, code="not_found")
    db.session.delete(h)
    db.session.commit()
    return ok({"deleted": True, "id": holiday_id})


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------

@admin_locations_bp.get("")
@login_required
def list_locations():
    rows = Location.query.order_by(Location.name.asc()).all()
    return ok([LocationSchema().dump(r) for r in rows])


@admin_locations_bp.post("")
@login_required
def create_location():
    try:
        data = LocationCreateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return fail("Datos inválidos", 422, code="validation_error", errors=err.messages)
    loc = Location(**data)
    db.session.add(loc)
    db.session.commit()
    log_activity("LOCATION_CREATE", f"Sede creada: {loc.name}")
    return ok(LocationSchema().dump(loc), status=201)


@admin_locations_bp.patch("/<int:location_id>")
@login_required
def update_location(location_id: int):
    loc = db.session.get(Location, location_id)
    if not loc:
        return fail("Sede no encontrada", 404, code="not_found")
    try:
        data = LocationCreateSchema().load(request.get_json(silent=True) or {}, partial=True)
    except ValidationError as err:
        return fail("Datos inválidos", 422, code="validation_error", errors=err.messages)
    for k, v in data.items():
        setattr(loc, k, v)
    db.session.commit()
    return ok(LocationSchema().dump(loc))


@admin_locations_bp.delete("/<int:location_id>")
@login_required
def delete_location(location_id: int):
    loc = db.session.get(Location, location_id)
    if not loc:
        return fail("Sede no encontrada", 404, code="not_found")
    if loc.slots.first() is not None or loc.appointments.first() is not None:
        loc.is_active = False
        db.session.commit()
        log_activity("LOCATION_SOFT_DELETE", f"Sede desactivada: {loc.name}")
        return ok({"soft_deleted": True, "id": location_id})
    db.session.delete(loc)
    db.session.commit()
    return ok({"deleted": True, "id": location_id})
