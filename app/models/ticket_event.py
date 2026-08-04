"""Audit trail for appointment (ticket) state changes."""

from __future__ import annotations

from app.extensions import db
from app.models.appointment import utcnow


class TicketEvent(db.Model):
    """One immutable row per ticket state change, used by the dashboard history."""

    __tablename__ = "ticket_events"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status = db.Column(db.String(20), nullable=True)
    to_status = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    username = db.Column(db.String(64), nullable=True)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "appointment_id": self.appointment_id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "user_id": self.user_id,
            "username": self.username,
            "note": self.note or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TicketEvent {self.appointment_id} {self.from_status}->{self.to_status}>"
