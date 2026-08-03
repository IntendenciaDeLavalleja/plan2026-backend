"""Admin authentication: 2-step login (credentials + email 2FA)."""

from __future__ import annotations

import random
import secrets
from time import perf_counter

from flask import Blueprint, current_app, g, request, session
from flask_login import current_user, login_user, logout_user
from marshmallow import ValidationError

from app.extensions import db, limiter
from app.models.user import AdminUser, TwoFactorCode
from app.services.email_service import send_2fa_email
from app.utils.logging_helper import log_activity
from app.utils.responses import fail, ok

admin_auth_bp = Blueprint("admin_auth", __name__)


def _log_login_stage(stage: str, started_at: float, *, result: str = "ok", user_id: int | None = None) -> None:
    current_app.logger.info(
        "auth_login request_id=%s stage=%s duration_ms=%s result=%s user_id=%s",
        getattr(g, "request_id", None),
        stage,
        int((perf_counter() - started_at) * 1000),
        result,
        user_id,
    )


def _new_captcha() -> tuple[str, int]:
    a = random.randint(2, 12)
    b = random.randint(2, 12)
    session["captcha_result"] = a + b
    return f"¿Cuánto es {a} + {b}?", a + b


@admin_auth_bp.get("/captcha")
def get_captcha():
    question, _answer = _new_captcha()
    return ok({"question": question})


@admin_auth_bp.post("/login")
@limiter.limit("10 per minute")
def login_step1():
    """Validate email + password + captcha. On success, send 2FA code via email."""
    request_started_at = perf_counter()
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    captcha = (data.get("captcha") or "").strip()

    if not email or not password:
        _log_login_stage("validate_payload", request_started_at, result="missing_fields")
        return fail("Email y contraseña son requeridos", 400, code="missing_fields")
    if not captcha:
        _log_login_stage("validate_payload", request_started_at, result="missing_captcha")
        return fail("Debe resolver la verificación de seguridad", 400, code="missing_captcha")

    expected = session.pop("captcha_result", None)
    if expected is None or str(expected) != str(captcha):
        log_activity("ADMIN_LOGIN_CAPTCHA_FAIL", "Verificación de seguridad inválida")
        _log_login_stage("validate_captcha", request_started_at, result="invalid")
        return fail("Verificación de seguridad inválida", 400, code="captcha_invalid")

    lookup_started_at = perf_counter()
    user = AdminUser.query.filter_by(email=email).first()
    _log_login_stage("lookup_user", lookup_started_at, result="found" if user else "not_found", user_id=user.id if user else None)
    password_started_at = perf_counter()
    if not user or not user.check_password(password):
        log_activity("ADMIN_LOGIN_FAIL", "Credenciales inválidas")
        _log_login_stage("verify_password", password_started_at, result="invalid", user_id=user.id if user else None)
        return fail("Credenciales inválidas", 401, code="invalid_credentials")
    _log_login_stage("verify_password", password_started_at, user_id=user.id)
    if not user.is_active:
        _log_login_stage("validate_account", request_started_at, result="disabled", user_id=user.id)
        return fail("La cuenta está deshabilitada", 403, code="account_disabled")

    persist_started_at = perf_counter()
    TwoFactorCode.query.filter_by(user_id=user.id, purpose="login", consumed_at=None).update(
        {TwoFactorCode.consumed_at: db.func.now()},
        synchronize_session=False,
    )
    code = "".join(secrets.choice("0123456789") for _ in range(6))
    tf = TwoFactorCode(user_id=user.id, code=code, purpose="login", ttl_minutes=10)
    db.session.add(tf)
    db.session.commit()
    _log_login_stage("persist_two_factor", persist_started_at, user_id=user.id)

    delivery_started_at = perf_counter()
    delivered = send_2fa_email(user.email, code)
    _log_login_stage("deliver_two_factor", delivery_started_at, result="accepted" if delivered else "failed", user_id=user.id)
    if not delivered:
        tf.consumed_at = db.func.now()
        db.session.commit()
        log_activity("ADMIN_LOGIN_2FA_DELIVERY_FAILED", "No se pudo entregar el segundo factor", user=user)
        return fail("No se pudo enviar el código de verificación. Intentá nuevamente.", 503, code="two_factor_delivery_failed")

    session["2fa_user_id"] = user.id
    session["2fa_challenge_id"] = tf.id
    log_activity("ADMIN_LOGIN_STEP1_SUCCESS", "Segundo factor solicitado", user=user)
    _log_login_stage("complete", request_started_at, user_id=user.id)
    return ok({"requires_2fa": True, "preview": _preview_email(user.email)})


@admin_auth_bp.post("/verify-2fa")
@limiter.limit("10 per minute")
def verify_2fa():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    if not code:
        return fail("Código requerido", 400, code="missing_code")

    user_id = session.get("2fa_user_id")
    challenge_id = session.get("2fa_challenge_id")
    if not user_id or not challenge_id:
        return fail("La sesión de verificación expiró", 401, code="session_expired")

    user = db.session.get(AdminUser, user_id)
    if not user:
        session.pop("2fa_user_id", None)
        return fail("Usuario no encontrado", 404, code="not_found")

    tf = db.session.get(TwoFactorCode, challenge_id)
    if tf is None or tf.user_id != user.id or tf.purpose != "login":
        session.pop("2fa_user_id", None)
        session.pop("2fa_challenge_id", None)
        return fail("La sesión de verificación expiró", 401, code="session_expired")
    if not tf or not tf.verify(code):
        log_activity("ADMIN_LOGIN_2FA_FAIL", f"Código 2FA incorrecto (id={user.id})", user=user)
        return fail("Código inválido o expirado", 400, code="invalid_code")

    tf.consumed_at = db.func.now()
    user.last_login_at = db.func.now()
    db.session.commit()

    session.clear()
    login_user(user)
    log_activity("ADMIN_LOGIN_2FA_SUCCESS", "Inicio de sesión exitoso", user=user)
    return ok({"user": user.to_dict()})


@admin_auth_bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        log_activity("ADMIN_LOGOUT", "Cierre de sesión")
    logout_user()
    session.clear()
    return ok({"logged_out": True})


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
