from marshmallow import Schema, fields, validate, EXCLUDE, ValidationError, validates_schema


class _BaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE


class LocationSchema(_BaseSchema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    address = fields.Str(allow_none=True, load_default="")
    phone = fields.Str(allow_none=True, load_default="")
    is_active = fields.Bool(load_default=True)


class LocationCreateSchema(LocationSchema):
    pass


class AvailabilityRuleSchema(_BaseSchema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=2, max=160))
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    weekdays = fields.List(fields.Int(validate=validate.Range(min=0, max=6)), required=True)
    start_time = fields.Time(required=True)
    end_time = fields.Time(required=True)
    slot_duration_minutes = fields.Int(load_default=20, validate=validate.Range(min=5, max=480))
    capacity_per_slot = fields.Int(load_default=1, validate=validate.Range(min=1, max=500))
    location_id = fields.Int(allow_none=True, load_default=None)
    team = fields.Str(allow_none=True, load_default=None)
    applies_to_all = fields.Bool(load_default=False)
    tribute_type_ids = fields.List(fields.Int(), load_default=list)
    is_active = fields.Bool(load_default=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @validates_schema
    def _validate_dates(self, data, **kwargs):
        if data.get("start_date") and data.get("end_date") and data["end_date"] < data["start_date"]:
            raise ValidationError({"end_date": ["La fecha de fin debe ser posterior a la fecha de inicio"]})
        if data.get("start_time") and data.get("end_time") and data["end_time"] <= data["start_time"]:
            raise ValidationError({"end_time": ["La hora de fin debe ser posterior a la hora de inicio"]})


class AvailabilityRuleCreateSchema(AvailabilityRuleSchema):
    pass


class AppointmentSlotSchema(_BaseSchema):
    id = fields.Int(dump_only=True)
    tribute_type_id = fields.Int(allow_none=True, load_default=None)
    location_id = fields.Int(allow_none=True, load_default=None)
    rule_id = fields.Int(allow_none=True, load_default=None)
    date = fields.Date(required=True)
    start_time = fields.Time(required=True)
    end_time = fields.Time(required=True)
    capacity = fields.Int(load_default=1, validate=validate.Range(min=1, max=500))
    reserved_count = fields.Int(dump_only=True)
    remaining = fields.Int(dump_only=True)
    is_blocked = fields.Bool(load_default=False)
    block_reason = fields.Str(allow_none=True, load_default=None)
    notes = fields.Str(allow_none=True, load_default=None)


class HolidaySchema(_BaseSchema):
    id = fields.Int(dump_only=True)
    date = fields.Date(required=True)
    reason = fields.Str(allow_none=True, load_default=None)
    is_full_day = fields.Bool(load_default=True)
    start_time = fields.Time(allow_none=True, load_default=None)
    end_time = fields.Time(allow_none=True, load_default=None)
