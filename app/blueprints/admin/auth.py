"""Separate dashboard JWT API and Flask-Login panel authentication flows."""

from __future__ import annotations

import secrets
from datetime import timedelta

from flask import Blueprint, current_app, request, session
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, jwt_required
from flask_login import current_user, login_user, logout_user

from app.extensions import db, limiter
from app.models.user import AdminUser, TwoFactorCode
from app.services.email_service import send_2fa_email
from app.utils.logging_helper import log_activity
from app.utils.responses import fail, ok

admin_auth_bp = Blueprint("admin_auth", __name__)


def _preview_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    return f"{local[:2]}{'*' * max(0, len(local) - 3)}{local[-1:] if len(local) > 2 else ''}@{domain}"


def _create_code(user: AdminUser) -> TwoFactorCode:
    TwoFactorCode.query.filter_by(user_id=user.id, purpose="login", consumed_at=None).update(
        {TwoFactorCode.consumed_at: db.func.now()}, synchronize_session=False,
    )
    code = current_app.config.get("DEV_TWO_FACTOR_CODE") or "".join(secrets.choice("0123456789") for _ in range(6))
    challenge = TwoFactorCode(user_id=user.id, code=code, purpose="login", ttl_minutes=10)
    db.session.add(challenge)
    db.session.commit()
    try:
        send_2fa_email(user.email, code)
    except Exception:
        current_app.logger.exception("Could not deliver administrative 2FA email")
    return challenge


def _access_token(user: AdminUser) -> str:
    return create_access_token(
        identity=str(user.id),
        additional_claims={"type": "access", "role": "superuser" if user.is_superuser else "admin", "is_superuser": bool(user.is_superuser)},
    )


def _dashboard_login(data: dict):
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return fail("Email y contraseña son requeridos", 400, code="missing_fields")
    user = AdminUser.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return fail("Credenciales inválidas", 401, code="invalid_credentials")
    if not user.is_active:
        return fail("La cuenta está deshabilitada", 403, code="account_disabled")
    challenge = _create_code(user)
    pending_token = create_access_token(
        identity=str(user.id),
        additional_claims={"type": "2fa_pending", "challenge_id": challenge.id},
        expires_delta=timedelta(minutes=10),
    )
    log_activity("DASHBOARD_LOGIN_STEP1", "Segundo factor solicitado", user=user)
    return ok({"requires_2fa": True, "pending_token": pending_token, "email_preview": _preview_email(user.email), "expires_in": 600})


def _panel_login(data: dict):
    """Panel-only step 1. It deliberately uses Flask session state."""
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if str(session.pop("captcha_result", "")) != str(data.get("captcha") or ""):
        return fail("Verificación de seguridad inválida", 400, code="captcha_invalid")
    user = AdminUser.query.filter_by(email=email).first()
    if not user or not user.check_password(password) or not user.is_active:
        return fail("Credenciales inválidas", 401, code="invalid_credentials")
    _create_code(user)
    session["panel_2fa_user_id"] = user.id
    return ok({"requires_2fa": True, "preview": _preview_email(user.email)})


@admin_auth_bp.post("/login")
@limiter.limit("10 per minute")
def login_step1():
    data = request.get_json(silent=True) or {}
    return _dashboard_login(data)


@admin_auth_bp.post("/verify-2fa")
@limiter.limit("10 per minute")
def verify_2fa():
    data = request.get_json(silent=True) or {}
    return _verify_dashboard_2fa(data)


@jwt_required()
def _verify_dashboard_2fa(data: dict):
    claims = get_jwt()
    if claims.get("type") != "2fa_pending":
        return fail("Token inválido para este endpoint", 403, code="invalid_token_type")
    user = db.session.get(AdminUser, int(get_jwt_identity()))
    challenge = db.session.get(TwoFactorCode, claims.get("challenge_id"))
    if not user or not user.is_active or not challenge or challenge.user_id != user.id or not challenge.verify((data.get("code") or "").strip()):
        return fail("Código inválido o expirado", 401, code="invalid_code")
    challenge.consumed_at = db.func.now()
    user.last_login_at = db.func.now()
    db.session.commit()
    log_activity("DASHBOARD_LOGIN_SUCCESS", "Inicio de sesión Bearer", user=user)
    return ok({"access_token": _access_token(user), "token_type": "Bearer", "expires_in": int(current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds()), "user": user.to_dict()})


@admin_auth_bp.post("/resend-2fa")
@jwt_required()
@limiter.limit("5 per 10 minutes")
def resend_2fa():
    if get_jwt().get("type") != "2fa_pending":
        return fail("Token inválido para este endpoint", 403, code="invalid_token_type")
    user = db.session.get(AdminUser, int(get_jwt_identity()))
    if not user or not user.is_active:
        return fail("Usuario no encontrado", 404, code="not_found")
    challenge = _create_code(user)
    pending_token = create_access_token(identity=str(user.id), additional_claims={"type": "2fa_pending", "challenge_id": challenge.id}, expires_delta=timedelta(minutes=10))
    return ok({"requires_2fa": True, "pending_token": pending_token, "email_preview": _preview_email(user.email), "expires_in": 600})


@admin_auth_bp.get("/me")
@jwt_required()
def me():
    if get_jwt().get("type") != "access":
        return fail("Token inválido", 403, code="invalid_token_type")
    user = db.session.get(AdminUser, int(get_jwt_identity()))
    if not user or not user.is_active:
        return fail("Usuario no encontrado", 404, code="not_found")
    return ok({"user": user.to_dict()})


@admin_auth_bp.post("/logout")
@jwt_required()
def logout():
    if get_jwt().get("type") == "access":
        user = db.session.get(AdminUser, int(get_jwt_identity()))
        if user:
            log_activity("DASHBOARD_LOGOUT", "Cierre de sesión Bearer", user=user)
    return ok({"ok": True})
