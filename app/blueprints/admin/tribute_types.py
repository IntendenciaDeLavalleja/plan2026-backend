"""Admin CRUD for tribute types."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required
from marshmallow import ValidationError

from app.extensions import db
from app.models.appointment import Appointment
from app.models.availability import AppointmentSlot
from app.models.tribute_type import TributeType
from app.schemas.tribute_type_schema import TributeTypeSchema
from app.utils.logging_helper import log_activity
from app.utils.responses import fail, ok, paginated

admin_tribute_types_bp = Blueprint("admin_tribute_types", __name__)


@admin_tribute_types_bp.get("")
@login_required
def list_tribute_types():
    page = int(request.args.get("page", 1) or 1)
    per_page = min(int(request.args.get("per_page", 50) or 50), 200)
    q = (request.args.get("q") or "").strip()
    include_inactive = (request.args.get("include_inactive") or "").lower() in {"1", "true", "yes"}

    query = TributeType.query
    if q:
        like = f"%{q}%"
        query = query.filter((TributeType.name.ilike(like)) | (TributeType.slug.ilike(like)))
    if not include_inactive:
        query = query.filter(TributeType.is_active.is_(True))

    total = query.count()
    rows = (
        query.order_by(TributeType.sort_order.asc(), TributeType.name.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return ok(paginated([TributeTypeSchema().dump(t) for t in rows], page, per_page, total))


@admin_tribute_types_bp.post("")
@login_required
def create_tribute_type():
    try:
        data = TributeTypeSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return fail("Datos inválidos", 422, code="validation_error", errors=err.messages)

    if TributeType.query.filter_by(name=data["name"]).first():
        return fail("Ya existe un tributo con ese nombre", 409, code="duplicate_name")

    tribute = TributeType(**data)
    db.session.add(tribute)
    db.session.commit()
    log_activity("TRIBUTE_CREATE", f"Tributo creado: {tribute.name}")
    return ok(TributeTypeSchema().dump(tribute), status=201)


@admin_tribute_types_bp.get("/<int:tribute_id>")
@login_required
def get_tribute_type(tribute_id: int):
    t = db.session.get(TributeType, tribute_id)
    if not t:
        return fail("Tributo no encontrado", 404, code="not_found")
    return ok(TributeTypeSchema().dump(t))


@admin_tribute_types_bp.patch("/<int:tribute_id>")
@login_required
def update_tribute_type(tribute_id: int):
    t = db.session.get(TributeType, tribute_id)
    if not t:
        return fail("Tributo no encontrado", 404, code="not_found")
    try:
        data = TributeTypeSchema().load(request.get_json(silent=True) or {}, partial=True)
    except ValidationError as err:
        return fail("Datos inválidos", 422, code="validation_error", errors=err.messages)

    for key, value in data.items():
        setattr(t, key, value)
    db.session.commit()
    log_activity("TRIBUTE_UPDATE", f"Tributo actualizado: {t.name}")
    return ok(TributeTypeSchema().dump(t))


@admin_tribute_types_bp.delete("/<int:tribute_id>")
@login_required
def delete_tribute_type(tribute_id: int):
    t = db.session.get(TributeType, tribute_id)
    if not t:
        return fail("Tributo no encontrado", 404, code="not_found")

    has_slots = AppointmentSlot.query.filter_by(tribute_type_id=t.id).first() is not None
    has_appointments = Appointment.query.filter_by(tribute_type_id=t.id).first() is not None

    if has_appointments:
        # Soft delete to preserve history
        t.is_active = False
        db.session.commit()
        log_activity("TRIBUTE_SOFT_DELETE", f"Tributo desactivado: {t.name}")
        return ok({"soft_deleted": True, "id": t.id})

    if has_slots:
        t.is_active = False
        db.session.commit()
        log_activity("TRIBUTE_SOFT_DELETE", f"Tributo desactivado (con slots): {t.name}")
        return ok({"soft_deleted": True, "id": t.id})

    db.session.delete(t)
    db.session.commit()
    log_activity("TRIBUTE_DELETE", f"Tributo eliminado: {t.name}")
    return ok({"deleted": True, "id": tribute_id})
