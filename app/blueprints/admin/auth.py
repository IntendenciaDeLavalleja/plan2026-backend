"""Admin authentication: 2-step login (credentials + email 2FA)."""

from __future__ import annotations

import random
import secrets

from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_user, logout_user
from marshmallow import ValidationError

from app.extensions import db, limiter
from app.models.user import AdminUser, TwoFactorCode
from app.services.email_service import send_2fa_email
from app.utils.logging_helper import log_activity
from app.utils.responses import fail, ok

admin_auth_bp = Blueprint("admin_auth", __name__)


def _new_captcha() -> tuple[str, int]:
    a = random.randint(2, 12)
    b = random.randint(2, 12)
    session["captcha_result"] = a + b
    return f"¿Cuánto es {a} + {b}?", a + b


@admin_auth_bp.get("/captcha")
def get_captcha():
    question, answer = _new_captcha()
    return ok({"question": question, "answer": answer})


@admin_auth_bp.post("/login")
@limiter.limit("10 per minute")
def login_step1():
    """Validate email + password + captcha. On success, send 2FA code via email."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    captcha = (data.get("captcha") or "").strip()

    if not email or not password:
        return fail("Email y contraseña son requeridos", 400, code="missing_fields")
    if not captcha:
        return fail("Debe resolver la verificación de seguridad", 400, code="missing_captcha")

    expected = session.pop("captcha_result", None)
    if expected is None or str(expected) != str(captcha):
        log_activity("ADMIN_LOGIN_CAPTCHA_FAIL", f"Captcha inválido para {email}")
        return fail("Verificación de seguridad inválida", 400, code="captcha_invalid")

    user = AdminUser.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        log_activity("ADMIN_LOGIN_FAIL", f"Credenciales inválidas: {email}")
        return fail("Credenciales inválidas", 401, code="invalid_credentials")
    if not user.is_active:
        return fail("La cuenta está deshabilitada", 403, code="account_disabled")

    code = "".join(secrets.choice("0123456789") for _ in range(6))
    tf = TwoFactorCode(user_id=user.id, code=code, purpose="login", ttl_minutes=10)
    db.session.add(tf)
    db.session.commit()

    try:
        send_2fa_email(user.email, code)
    except Exception:
        # We don't fail the login if email can't be sent immediately; admin can retry.
        pass

    session["2fa_user_id"] = user.id
    log_activity("ADMIN_LOGIN_STEP1_SUCCESS", f"2FA enviado a {user.email}", user=user)
    return ok({"requires_2fa": True, "preview": _preview_email(user.email)})


@admin_auth_bp.post("/verify-2fa")
@limiter.limit("10 per minute")
def verify_2fa():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    if not code:
        return fail("Código requerido", 400, code="missing_code")

    user_id = session.get("2fa_user_id")
    if not user_id:
        return fail("La sesión de verificación expiró", 401, code="session_expired")

    user = db.session.get(AdminUser, user_id)
    if not user:
        session.pop("2fa_user_id", None)
        return fail("Usuario no encontrado", 404, code="not_found")

    tf = (
        TwoFactorCode.query.filter_by(user_id=user.id, consumed_at=None, purpose="login")
        .order_by(TwoFactorCode.created_at.desc())
        .first()
    )
    if not tf or not tf.verify(code):
        log_activity("ADMIN_LOGIN_2FA_FAIL", f"Código 2FA incorrecto (id={user.id})", user=user)
        return fail("Código inválido o expirado", 400, code="invalid_code")

    tf.consumed_at = db.func.now()
    user.last_login_at = db.func.now()
    db.session.commit()

    login_user(user)
    session.pop("2fa_user_id", None)
    log_activity("ADMIN_LOGIN_2FA_SUCCESS", "Inicio de sesión exitoso", user=user)
    return ok({"user": user.to_dict()})


@admin_auth_bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        log_activity("ADMIN_LOGOUT", "Cierre de sesión")
    logout_user()
    return ok({"ok": True})


@admin_auth_bp.get("/me")
def me():
    if not current_user.is_authenticated:
        return fail("No autenticado", 401, code="unauthorized")
    return ok({"user": current_user.to_dict()})


def _preview_email(email: str) -> str:
    if "@" not in email or len(email) < 6:
        return "***"
    local, _, domain = email.partition("@")
    if len(local) <= 3:
        masked = "*" * len(local)
    else:
        masked = local[:2] + "*" * (len(local) - 3) + local[-1]
    return f"{masked}@{domain}"
