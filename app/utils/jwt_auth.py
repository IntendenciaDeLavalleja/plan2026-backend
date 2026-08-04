"""JWT authorization used exclusively by dashboard API routes."""

from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from app.extensions import db
from app.models.user import AdminUser
from app.utils.responses import fail


def get_dashboard_admin() -> AdminUser | None:
    return getattr(g, "dashboard_admin", None)


def jwt_admin_required(view):
    @wraps(view)
    @jwt_required()
    def wrapped(*args, **kwargs):
        claims = get_jwt()
        if claims.get("type") != "access":
            return fail("Token inválido", 403, code="invalid_token_type")
        user = db.session.get(AdminUser, int(get_jwt_identity()))
        if not user or not user.is_active:
            return fail("Autenticación requerida", 401, code="unauthorized")
        g.dashboard_admin = user
        return view(*args, **kwargs)
    return wrapped


def jwt_superuser_required(view):
    @wraps(view)
    @jwt_admin_required
    def wrapped(*args, **kwargs):
        if not get_dashboard_admin().is_superuser:
            return fail("Se requieren permisos de superadministrador", 403, code="superuser_required")
        return view(*args, **kwargs)
    return wrapped
