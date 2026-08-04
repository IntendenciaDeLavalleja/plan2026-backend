from __future__ import annotations

import re
from typing import Any

from flask import current_app, request
from flask_login import current_user

from app.extensions import limiter

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_PHONE_RE = re.compile(r"^[\d\s+()\-]{6,30}$")
_CI_RE = re.compile(r"^[\d.\-]{6,12}$")


def is_valid_email(value: str | None) -> bool:
    return bool(value) and bool(_EMAIL_RE.match(value.strip()))


def is_valid_phone(value: str | None) -> bool:
    return bool(value) and bool(_PHONE_RE.match(value.strip()))


def is_valid_ci(value: str | None) -> bool:
    if not value:
        return False
    return bool(_CI_RE.match(value.strip()))


def require_json() -> dict:
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict() if request.form else {}
    if not isinstance(data, dict):
        from app.utils.responses import fail
        raise ValueError("Cuerpo de la petición inválido")
    return data


def require_admin():
    if not current_user.is_authenticated:
        from flask_login import login_required
        # let Flask-Login handle the response via the unauthorized handler
        from app.utils.responses import fail
        return fail("Autenticación requerida", 401, code="unauthorized")
    return None


def apply_rate_limit(rule: str):
    """Decorator helper for adding limiter rules to specific endpoints."""
    return limiter.limit(rule)


def app_setting(key: str, default: Any = None) -> Any:
    """Fetch a SystemSetting value (imported lazily to avoid circular deps)."""
    from app.models.setting import SystemSetting
    return SystemSetting.get(key, default)
