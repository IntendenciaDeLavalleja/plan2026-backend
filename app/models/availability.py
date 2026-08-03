from datetime import datetime, date, time, timezone

from app.extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --- Association table: which tribute types an availability rule applies to ---
availability_rule_tribute_types = db.Table(
    "availability_rule_tribute_types",
    db.Column("rule_id", db.Integer, db.ForeignKey("availability_rules.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tribute_type_id", db.Integer, db.ForeignKey("tribute_types.id", ondelete="CASCADE"), primary_key=True),
)


class Location(db.Model):
    """Oficina / sede donde se atiende."""

    __tablename__ = "locations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(60), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    slots = db.relationship("AppointmentSlot", backref="location", lazy="dynamic")
    appointments = db.relationship("Appointment", backref="location", lazy="dynamic")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address or "",
            "phone": self.phone or "",
            "is_active": bool(self.is_active),
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Location {self.name}>"


class AvailabilityRule(db.Model):
    """Regla recurrente de disponibilidad (rango de fechas + días de semana + horario)."""

    __tablename__ = "availability_rules"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    # Lista de días de semana (0=lunes ... 6=domingo)
    weekdays = db.Column(db.JSON, nullable=False, default=list)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    slot_duration_minutes = db.Column(db.Integer, nullable=False, default=20)
    capacity_per_slot = db.Column(db.Integer, nullable=False, default=1)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    team = db.Column(db.String(120), nullable=True)
    applies_to_all = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    tribute_types = db.relationship(
        "TributeType",
        secondary=availability_rule_tribute_types,
    )
    location = db.relationship("Location")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "weekdays": list(self.weekdays or []),
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "slot_duration_minutes": self.slot_duration_minutes,
            "capacity_per_slot": self.capacity_per_slot,
            "location_id": self.location_id,
            "location_name": self.location.name if self.location else None,
            "team": self.team,
            "applies_to_all": bool(self.applies_to_all),
            "tribute_type_ids": [t.id for t in self.tribute_types],
            "is_active": bool(self.is_active),
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AvailabilityRule {self.name}>"


# Backwards-compatible alias for legacy code paths (Table, not a class)
AvailabilityRuleTributeType = availability_rule_tribute_types  # type: ignore[misc]


class AppointmentSlot(db.Model):
    """Slot concreto (fecha + hora + tributo) que se ofrece a los vecinos."""

    __tablename__ = "appointment_slots"

    id = db.Column(db.Integer, primary_key=True)
    tribute_type_id = db.Column(db.Integer, db.ForeignKey("tribute_types.id", ondelete="CASCADE"), nullable=True)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    rule_id = db.Column(db.Integer, db.ForeignKey("availability_rules.id", ondelete="SET NULL"), nullable=True)

    date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=1)
    reserved_count = db.Column(db.Integer, nullable=False, default=0)
    is_blocked = db.Column(db.Boolean, default=False, nullable=False)
    block_reason = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    appointments = db.relationship("Appointment", backref="slot", lazy="dynamic")

    __table_args__ = (
        db.UniqueConstraint("tribute_type_id", "location_id", "date", "start_time", name="uq_slot_unique"),
        db.Index("ix_slot_date_tribute", "date", "tribute_type_id"),
    )

    @property
    def remaining(self) -> int:
        return max(0, self.capacity - self.reserved_count)

    @property
    def is_full(self) -> bool:
        return self.remaining <= 0

    def to_dict(self, include_capacity: bool = True) -> dict:
        data = {
            "id": self.id,
            "tribute_type_id": self.tribute_type_id,
            "location_id": self.location_id,
            "location_name": self.location.name if self.location else None,
            "rule_id": self.rule_id,
            "date": self.date.isoformat() if self.date else None,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "is_blocked": bool(self.is_blocked),
            "block_reason": self.block_reason or "",
            "notes": self.notes or "",
        }
        if include_capacity:
            data["capacity"] = self.capacity
            data["reserved_count"] = self.reserved_count
            data["remaining"] = self.remaining
        return data

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AppointmentSlot {self.date} {self.start_time}>"


class HolidayOrBlockedDay(db.Model):
    """Días feriados o bloqueados a nivel general (no se generan slots)."""

    __tablename__ = "holidays_or_blocked_days"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True, index=True)
    reason = db.Column(db.String(255), nullable=True)
    is_full_day = db.Column(db.Boolean, default=True, nullable=False)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "reason": self.reason or "",
            "is_full_day": bool(self.is_full_day),
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Holiday {self.date}>"
