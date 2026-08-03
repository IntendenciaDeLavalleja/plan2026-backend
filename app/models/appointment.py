from datetime import datetime

from app.extensions import db

APPOINTMENT_STATUSES = (
    "reserved",
    "confirmed",
    "attended",
    "cancelled",
    "no_show",
)


class Appointment(db.Model):
    """Reserva confirmada por un vecino."""

    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    reservation_code = db.Column(db.String(40), unique=True, nullable=False, index=True)

    tribute_type_id = db.Column(db.Integer, db.ForeignKey("tribute_types.id", ondelete="SET NULL"), nullable=True)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    slot_id = db.Column(db.Integer, db.ForeignKey("appointment_slots.id", ondelete="SET NULL"), nullable=True)

    # Citizen data
    citizen_name = db.Column(db.String(160), nullable=False)
    citizen_document = db.Column(db.String(20), nullable=False, index=True)
    phone = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    reference_value = db.Column(db.String(80), nullable=True)
    comments = db.Column(db.Text, nullable=True)

    # Booking info
    status = db.Column(db.String(20), default="reserved", nullable=False, index=True)
    internal_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    def to_public_dict(self) -> dict:
        """Public-facing serializer — no internal notes."""
        slot = self.slot
        tribute = self.tribute_type
        location = self.location
        return {
            "id": self.id,
            "reservation_code": self.reservation_code,
            "status": self.status,
            "tribute_type": {
                "id": tribute.id,
                "name": tribute.name,
                "icon_key": tribute.icon_key or "document",
            } if tribute else None,
            "location": {
                "id": location.id,
                "name": location.name,
                "address": location.address or "",
            } if location else None,
            "citizen": {
                "name": self.citizen_name,
                "document": self.citizen_document,
                "phone": self.phone,
                "email": self.email or "",
                "reference_value": self.reference_value or "",
            },
            "comments": self.comments or "",
            "date": slot.date.isoformat() if slot and slot.date else None,
            "start_time": slot.start_time.strftime("%H:%M") if slot and slot.start_time else None,
            "end_time": slot.end_time.strftime("%H:%M") if slot and slot.end_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_admin_dict(self) -> dict:
        data = self.to_public_dict()
        data["internal_notes"] = self.internal_notes or ""
        data["cancelled_at"] = self.cancelled_at.isoformat() if self.cancelled_at else None
        data["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        return data

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Appointment {self.reservation_code} status={self.status}>"
