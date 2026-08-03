from marshmallow import Schema, fields, validate, EXCLUDE, validates_schema, ValidationError, validates

import re

_CI_RE = re.compile(r"^[\d.\-]{6,12}$")
_PHONE_RE = re.compile(r"^[\d\s+()\-]{6,30}$")


def _normalize_ci(value: str) -> str:
    if not value:
        return value
    return re.sub(r"[\s]", "", value).strip()


def _validate_ci(value: str) -> None:
    cleaned = _normalize_ci(value)
    if not _CI_RE.match(cleaned):
        raise ValidationError("Cédula inválida. Ingrese sólo números, puntos o guiones (6 a 12 caracteres).")


def _validate_phone(value: str) -> None:
    if not _PHONE_RE.match(value.strip()):
        raise ValidationError("Teléfono inválido.")


class _BaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE


class AppointmentCreateSchema(_BaseSchema):
    tribute_type_id = fields.Int(required=True)
    slot_id = fields.Int(required=True)
    citizen_name = fields.Str(required=True, validate=validate.Length(min=3, max=160))
    citizen_document = fields.Str(required=True, validate=validate.Length(min=6, max=20))
    phone = fields.Str(required=True, validate=validate.Length(min=6, max=40))
    email = fields.Email(allow_none=True, load_default=None)
    reference_value = fields.Str(allow_none=True, load_default=None, validate=validate.Length(max=80))
    comments = fields.Str(allow_none=True, load_default=None, validate=validate.Length(max=1000))
    accept_terms = fields.Bool(required=True)

    @validates("citizen_document")
    def _check_ci(self, value, **kwargs):
        _validate_ci(value)

    @validates("phone")
    def _check_phone(self, value, **kwargs):
        _validate_phone(value)

    @validates_schema
    def _check_terms(self, data, **kwargs):
        if not data.get("accept_terms"):
            raise ValidationError({"accept_terms": ["Debe aceptar los términos para continuar"]})


class AppointmentAdminUpdateSchema(_BaseSchema):
    status = fields.Str(validate=validate.OneOf(["reserved", "confirmed", "attended", "cancelled", "no_show"]))
    internal_notes = fields.Str(allow_none=True, load_default=None)
    slot_id = fields.Int(allow_none=True, load_default=None)


class AppointmentPublicSchema(_BaseSchema):
    """Serializer used in admin/listing responses."""
    id = fields.Int(dump_only=True)
    reservation_code = fields.Str()
    status = fields.Str()
    tribute_type_id = fields.Int(allow_none=True)
    location_id = fields.Int(allow_none=True)
    slot_id = fields.Int()
    citizen_name = fields.Str()
    citizen_document = fields.Str()
    phone = fields.Str()
    email = fields.Str(allow_none=True)
    reference_value = fields.Str(allow_none=True)
    comments = fields.Str(allow_none=True)
    internal_notes = fields.Str(allow_none=True)
    date = fields.Date(allow_none=True)
    start_time = fields.Time(allow_none=True)
    end_time = fields.Time(allow_none=True)
    created_at = fields.DateTime(allow_none=True)
    updated_at = fields.DateTime(allow_none=True)
    cancelled_at = fields.DateTime(allow_none=True)


class AppointmentAdminSchema(AppointmentPublicSchema):
    date = fields.Method("get_slot_date", dump_only=True, allow_none=True)
    start_time = fields.Method("get_slot_start_time", dump_only=True, allow_none=True)
    end_time = fields.Method("get_slot_end_time", dump_only=True, allow_none=True)

    @staticmethod
    def get_slot_date(appointment):
        slot = appointment.slot
        return slot.date.isoformat() if slot and slot.date else None

    @staticmethod
    def get_slot_start_time(appointment):
        slot = appointment.slot
        return slot.start_time.strftime("%H:%M") if slot and slot.start_time else None

    @staticmethod
    def get_slot_end_time(appointment):
        slot = appointment.slot
        return slot.end_time.strftime("%H:%M") if slot and slot.end_time else None
