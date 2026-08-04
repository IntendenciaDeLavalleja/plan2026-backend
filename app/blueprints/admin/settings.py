"""Admin system settings."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required
from marshmallow import ValidationError

from app.extensions import db
from app.models.setting import SystemSetting
from app.schemas.appointment_schema import SystemSettingSchema, SystemSettingUpdateSchema
from app.utils.responses import fail, ok

admin_settings_bp = Blueprint("admin_settings", __name__)


DEFAULT_SETTINGS = [
    ("system_name", "Sistema de Agenda – Plan 2026", "string", "Nombre del sistema"),
    ("welcome_message", "Bienvenido al sistema de agenda electrónica de la Intendencia de Lavalleja.", "string", "Mensaje de bienvenida"),
    ("office_address", "José Batlle y Ordóñez 546, Minas, Lavalleja", "string", "Dirección de la oficina"),
    ("office_hours", "Lunes a viernes de 09:00 a 16:00 hs", "string", "Horario de atención"),
    ("contact_email", "agenda@lavalleja.gub.uy", "string", "Email de contacto"),
    ("contact_phone", "+598 444 22222", "string", "Teléfono de contacto"),
    ("legal_notice", "Los datos personales proporcionados serán tratados conforme a la legislación vigente.", "string", "Aviso legal"),
    ("receipt_footer", "Intendencia de Lavalleja · Amnistía Financiera", "string", "Pie de comprobante"),
    ("max_reservations_per_document", 1, "int", "Máximo de reservas activas por documento"),
    ("min_anticipation_hours", 1, "int", "Anticipación mínima en horas"),
    ("max_anticipation_days", 90, "int", "Anticipación máxima en días"),
    ("public_cancellation_enabled", True, "bool", "Permitir cancelación pública"),
]


def ensure_defaults():
    for key, value, vtype, desc in DEFAULT_SETTINGS:
        if SystemSetting.query.filter_by(key=key).first() is None:
            SystemSetting.set(key, value, vtype, desc)
            db.session.commit()


@admin_settings_bp.get("")
@login_required
def list_settings():
    ensure_defaults()
    rows = SystemSetting.query.order_by(SystemSetting.key.asc()).all()
    return ok([SystemSettingSchema().dump(r) for r in rows])


@admin_settings_bp.get("/<string:key>")
@login_required
def get_setting(key: str):
    row = SystemSetting.query.filter_by(key=key).first()
    if not row:
        return fail("Configuración no encontrada", 404, code="not_found")
    return ok(SystemSettingSchema().dump(row))


@admin_settings_bp.put("/<string:key>")
@login_required
def update_setting(key: str):
    try:
        data = SystemSettingUpdateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return fail("Datos inválidos", 422, code="validation_error", errors=err.messages)

    row = SystemSetting.query.filter_by(key=key).first()
    if not row:
        row = SystemSetting(key=key, value_type=data["value_type"])
        db.session.add(row)
    row.value_type = data["value_type"]
    if data["value_type"] == "json":
        import json
        row.value = json.dumps(data["value"], ensure_ascii=False)
    else:
        row.value = str(data["value"])
    if data.get("description") is not None:
        row.description = data["description"]
    db.session.commit()
    return ok(SystemSettingSchema().dump(row))
