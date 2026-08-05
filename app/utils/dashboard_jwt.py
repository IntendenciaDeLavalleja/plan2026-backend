"""JWT authorization boundary for the dashboard SPA only."""

from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from app.extensions import db
from app.models.user import AdminUser
from app.utils.responses import fail


def current_dashboard_admin():
    return getattr(g, "dashboard_admin", None)


def jwt_admin_required(view):
    @wraps(view)
    @jwt_required()
    def wrapped(*args, **kwargs):
        if get_jwt().get("type") != "access":
            return fail("Token inválido", 403, code="invalid_token_type")
        user = db.session.get(AdminUser, int(get_jwt_identity()))
        if not user or not user.is_active:
            return fail("Autenticación requerida", 401, code="unauthorized")
        g.dashboard_admin = user
        return view(*args, **kwargs)
    return wrapped
