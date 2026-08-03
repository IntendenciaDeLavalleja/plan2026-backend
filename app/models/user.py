from datetime import datetime, timezone
from flask_login import UserMixin
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

ph = PasswordHasher()


class AdminUser(UserMixin, db.Model):
    """Backend admin user (panel administrativo)."""

    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_superuser = db.Column(db.Boolean, default=False, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    two_factor_codes = db.relationship("TwoFactorCode", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    activity_logs = db.relationship("ActivityLog", backref="owner", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = ph.hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        try:
            return ph.verify(self.password_hash, password)
        except (VerifyMismatchError, Exception):
            return False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": bool(self.is_active),
            "is_superuser": bool(self.is_superuser),
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AdminUser {self.username}>"


class TwoFactorCode(db.Model):
    """Single-use 2FA code stored as a hash."""

    __tablename__ = "two_factor_codes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False)
    code_hash = db.Column(db.String(255), nullable=False)
    purpose = db.Column(db.String(40), default="login", nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    consumed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        db.Index("ix_two_factor_codes_login_lookup", "user_id", "purpose", "consumed_at", "created_at"),
    )

    def __init__(self, user_id: int, code: str, purpose: str = "login", ttl_minutes: int = 10) -> None:
        from datetime import timedelta

        self.user_id = user_id
        self.code_hash = ph.hash(code)
        self.purpose = purpose
        self.expires_at = utcnow() + timedelta(minutes=ttl_minutes)

    def verify(self, code: str) -> bool:
        if self.consumed_at is not None or utcnow() > self.expires_at:
            return False
        try:
            return ph.verify(self.code_hash, code)
        except (VerifyMismatchError, Exception):
            return False


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    username = db.Column(db.String(64), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    timestamp = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ActivityLog {self.action} by {self.username}>"
