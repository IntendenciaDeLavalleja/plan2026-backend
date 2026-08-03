from __future__ import annotations

from functools import wraps

from flask import jsonify
from flask_login import current_user, login_required


def require_superuser(view):
    """Require an authenticated administrator with superuser privileges."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_superuser:
            return jsonify({
                "ok": False,
                "error": {
                    "message": "Se requieren permisos de superadministrador",
                    "code": "superuser_required",
                },
            }), 403
        return view(*args, **kwargs)

    return wrapped