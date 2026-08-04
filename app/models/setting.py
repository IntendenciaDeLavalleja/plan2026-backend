from datetime import datetime

from app.extensions import db


class SystemSetting(db.Model):
    """Configuración general del sistema (clave/valor tipado)."""

    __tablename__ = "system_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    value_type = db.Column(db.String(20), default="string", nullable=False)  # string|int|bool|json
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.coerced_value(),
            "value_type": self.value_type,
            "description": self.description or "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def coerced_value(self):
        import json

        if self.value is None:
            return None
        try:
            if self.value_type == "int":
                return int(self.value)
            if self.value_type == "bool":
                return self.value.strip().lower() in {"1", "true", "yes", "on"}
            if self.value_type == "json":
                return json.loads(self.value)
        except Exception:
            return self.value
        return self.value

    @classmethod
    def get(cls, key: str, default=None):
        row = cls.query.filter_by(key=key).first()
        if not row:
            return default
        return row.coerced_value()

    @classmethod
    def set(cls, key: str, value, value_type: str = "string", description: str | None = None):
        import json

        row = cls.query.filter_by(key=key).first()
        if row is None:
            row = cls(key=key, description=description, value_type=value_type)
            db.session.add(row)
        row.value_type = value_type
        if value is None:
            row.value = None
        elif value_type == "json":
            row.value = json.dumps(value, ensure_ascii=False)
        else:
            row.value = str(value)
        if description is not None:
            row.description = description
        return row

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SystemSetting {self.key}>"
