"""Logging helper utilities."""

from __future__ import annotations

from flask import current_app, request
from flask_login import current_user

from app.extensions import db
from app.models.user import ActivityLog


def log_activity(action: str, details: str | None = None, user=None) -> None:
    """Persist an activity log entry without disrupting the primary operation."""
    try:
        user_id = None
        username = "anonymous"

        if user is not None:
            user_id = getattr(user, "id", None)
            username = getattr(user, "username", "anonymous")
        elif current_user and current_user.is_authenticated:
            user_id = current_user.id
            username = current_user.username

        log = ActivityLog(
            user_id=user_id,
            username=username,
            action=action,
            details=details,
            ip_address=(request.remote_addr if request else None),
            user_agent=((request.user_agent.string if request else "") or "")[:512],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:  # pragma: no cover
        current_app.logger.exception("Could not persist activity log")
