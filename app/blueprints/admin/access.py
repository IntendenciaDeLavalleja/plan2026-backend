from __future__ import annotations

import csv
from io import StringIO

from flask import Blueprint, make_response, request
from flask_login import current_user
from sqlalchemy import or_

from app.extensions import db
from app.models.user import ActivityLog, AdminUser
from app.utils.authorization import require_superuser
from app.utils.logging_helper import log_activity
from app.utils.responses import fail, ok, paginated

admin_access_bp = Blueprint("admin_access", __name__)


@admin_access_bp.get("/users")
@require_superuser
def list_users():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 25, type=int), 1), 100)
    query = AdminUser.query.order_by(AdminUser.username.asc())
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return ok(paginated(
        [user.to_dict() for user in result.items],
        result.page,
        result.per_page,
        result.total,
    ))


@admin_access_bp.post("/users")
@require_superuser
def create_user():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip() or None
    is_superuser = bool(data.get("is_superuser", False))
    is_active = bool(data.get("is_active", True))

    if not username or not email or not password:
        return fail("Username, email y contraseña son requeridos", 400, code="missing_fields")
    if len(username) > 64 or len(email) > 120 or len(password) < 12:
        return fail("El username/email son demasiado largos y la contraseña debe tener al menos 12 caracteres", 400, code="invalid_fields")
    if AdminUser.query.filter(or_(AdminUser.username == username, AdminUser.email == email)).first():
        return fail("Ya existe un usuario con ese username o email", 409, code="user_exists")

    user = AdminUser(
        username=username,
        email=email,
        full_name=full_name,
        is_superuser=is_superuser,
        is_active=is_active,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    log_activity("ADMIN_USER_CREATED", f"Usuario creado: {username}", user=current_user)
    return ok(user.to_dict(), status=201)


@admin_access_bp.patch("/users/<int:user_id>/password")
@require_superuser
def change_user_password(user_id: int):
    user = db.session.get(AdminUser, user_id)
    if not user:
        return fail("Usuario no encontrado", 404, code="user_not_found")

    data = request.get_json(silent=True) or {}
    password = data.get("password") or ""
    if len(password) < 12:
        return fail("La contraseña debe tener al menos 12 caracteres", 400, code="invalid_password")

    user.set_password(password)
    db.session.commit()
    log_activity("ADMIN_USER_PASSWORD_CHANGED", f"Contraseña actualizada: {user.username}", user=current_user)
    return ok({"id": user.id})


@admin_access_bp.patch("/users/<int:user_id>")
@require_superuser
def update_user(user_id: int):
    user = db.session.get(AdminUser, user_id)
    if not user:
        return fail("Usuario no encontrado", 404, code="user_not_found")

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    full_name = (data.get("full_name") or "").strip() or None
    password = data.get("password") or ""
    is_superuser = bool(data.get("is_superuser", False))
    is_active = bool(data.get("is_active", True))

    if not username or not email:
        return fail("Username y email son requeridos", 400, code="missing_fields")
    if len(username) > 64 or len(email) > 120 or (password and len(password) < 12):
        return fail("Los datos no son válidos; la contraseña debe tener al menos 12 caracteres", 400, code="invalid_fields")
    duplicate = AdminUser.query.filter(
        or_(AdminUser.username == username, AdminUser.email == email),
        AdminUser.id != user.id,
    ).first()
    if duplicate:
        return fail("Ya existe otro usuario con ese username o email", 409, code="user_exists")
    if user.is_superuser and not is_superuser and AdminUser.query.filter_by(is_superuser=True, is_active=True).count() <= 1:
        return fail("Debe existir al menos un superadministrador activo", 400, code="last_superuser_forbidden")
    if user.id == current_user.id and not is_active:
        return fail("No puede deshabilitar su propia cuenta", 400, code="self_disable_forbidden")

    user.username = username
    user.email = email
    user.full_name = full_name
    user.is_superuser = is_superuser
    user.is_active = is_active
    if password:
        user.set_password(password)
    db.session.commit()
    log_activity("ADMIN_USER_UPDATED", f"Usuario actualizado: {user.username}", user=current_user)
    return ok(user.to_dict())


@admin_access_bp.delete("/users/<int:user_id>")
@require_superuser
def delete_user(user_id: int):
    user = db.session.get(AdminUser, user_id)
    if not user:
        return fail("Usuario no encontrado", 404, code="user_not_found")
    if user.id == current_user.id:
        return fail("No puede eliminar su propia cuenta", 400, code="self_delete_forbidden")
    if user.is_superuser and AdminUser.query.filter_by(is_superuser=True, is_active=True).count() <= 1:
        return fail("Debe existir al menos un superadministrador activo", 400, code="last_superuser_forbidden")

    username = user.username
    db.session.delete(user)
    db.session.commit()
    log_activity("ADMIN_USER_DELETED", f"Usuario eliminado: {username}", user=current_user)
    return ok({"id": user_id, "deleted": True})


@admin_access_bp.get("/activity-logs")
@require_superuser
def list_activity_logs():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 50, type=int), 1), 100)
    query = ActivityLog.query.order_by(ActivityLog.timestamp.desc(), ActivityLog.id.desc())
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return ok(paginated(
        [log.to_dict() for log in result.items],
        result.page,
        result.per_page,
        result.total,
    ))


@admin_access_bp.get("/activity-logs.csv")
@require_superuser
def download_activity_logs():
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["ID", "Fecha", "Usuario", "Acción", "Detalle", "IP", "User-Agent"])
    for log in ActivityLog.query.order_by(ActivityLog.timestamp.desc(), ActivityLog.id.desc()).all():
        writer.writerow([
            log.id,
            log.timestamp.isoformat() if log.timestamp else "",
            log.username or "",
            log.action,
            log.details or "",
            log.ip_address or "",
            log.user_agent or "",
        ])

    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=logs-sistema.csv"
    return response
