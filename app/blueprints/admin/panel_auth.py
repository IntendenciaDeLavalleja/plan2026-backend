"""Flask-Login-only authentication endpoints for the HTML admin panel."""

from __future__ import annotations

import random

from flask import Blueprint, request, session
from flask_login import login_user

from app.blueprints.admin.auth import _panel_login
from app.extensions import db, limiter
from app.models.user import AdminUser, TwoFactorCode
from app.utils.logging_helper import log_activity
from app.utils.responses import fail, ok

panel_auth_bp = Blueprint("panel_auth", __name__)


@panel_auth_bp.get("/admin/captcha")
def captcha():
    left, right = random.randint(2, 12), random.randint(2, 12)
    session["captcha_result"] = left + right
    return ok({"question": f"¿Cuánto es {left} + {right}?"})


@panel_auth_bp.post("/admin/login")
@limiter.limit("10 per minute")
def login():
    return _panel_login(request.get_json(silent=True) or request.form.to_dict() or {})


@panel_auth_bp.post("/admin/verify-2fa")
@limiter.limit("10 per minute")
def verify_2fa():
    user = db.session.get(AdminUser, session.get("panel_2fa_user_id"))
    challenge = TwoFactorCode.query.filter_by(user_id=user.id, purpose="login", consumed_at=None).order_by(TwoFactorCode.created_at.desc()).first() if user else None
    code = (request.get_json(silent=True) or request.form.to_dict() or {}).get("code", "").strip()
    if not challenge or not challenge.verify(code):
        return fail("Código inválido o expirado", 400, code="invalid_code")
    challenge.consumed_at = db.func.now()
    user.last_login_at = db.func.now()
    login_user(user, remember=False)
    session.pop("panel_2fa_user_id", None)
    db.session.commit()
    log_activity("PANEL_LOGIN_SUCCESS", "Inicio de sesión por panel", user=user)
    return ok({"user": user.to_dict()})
