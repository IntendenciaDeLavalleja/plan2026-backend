from datetime import datetime
from sqlalchemy import event

from app.extensions import db


def _slugify(value: str) -> str:
    import re
    import unicodedata

    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "tributo"


class TributeType(db.Model):
    """Tipos de adeudos / tributos que atiende la Intendencia."""

    __tablename__ = "tribute_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    icon_key = db.Column(db.String(80), nullable=True)  # clave de icono usada en el frontend
    requirements_text = db.Column(db.Text, nullable=True)
    default_duration_minutes = db.Column(db.Integer, default=20, nullable=False)

    requires_padron = db.Column(db.Boolean, default=False, nullable=False)
    requires_matricula = db.Column(db.Boolean, default=False, nullable=False)
    requires_document = db.Column(db.Boolean, default=True, nullable=False)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=100, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # relationships
    slots = db.relationship("AppointmentSlot", backref="tribute_type", lazy="dynamic")
    appointments = db.relationship("Appointment", backref="tribute_type", lazy="dynamic")

    def to_dict(self, include_meta: bool = True) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description or "",
            "icon_key": self.icon_key or "document",
            "requirements_text": self.requirements_text or "",
            "default_duration_minutes": self.default_duration_minutes,
            "requires_padron": bool(self.requires_padron),
            "requires_matricula": bool(self.requires_matricula),
            "requires_document": bool(self.requires_document),
            "is_active": bool(self.is_active),
            "sort_order": self.sort_order,
        }
        if include_meta:
            data["created_at"] = self.created_at.isoformat() if self.created_at else None
            data["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        return data

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TributeType {self.name}>"


@event.listens_for(TributeType, "before_insert")
@event.listens_for(TributeType, "before_update")
def _ensure_slug(mapper, connection, target):  # pragma: no cover
    if not target.slug and target.name:
        target.slug = _slugify(target.name)
