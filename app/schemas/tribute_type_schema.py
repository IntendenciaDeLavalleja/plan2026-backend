from marshmallow import Schema, fields, validate, EXCLUDE


class _BaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE


class TributeTypeSchema(_BaseSchema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=2, max=160))
    slug = fields.Str(allow_none=True, load_default=None)
    description = fields.Str(allow_none=True, load_default="")
    icon_key = fields.Str(allow_none=True, load_default="document")
    requirements_text = fields.Str(allow_none=True, load_default="")
    default_duration_minutes = fields.Int(load_default=20, validate=validate.Range(min=5, max=480))
    requires_padron = fields.Bool(load_default=False)
    requires_matricula = fields.Bool(load_default=False)
    requires_document = fields.Bool(load_default=True)
    is_active = fields.Bool(load_default=True)
    sort_order = fields.Int(load_default=100)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class TributeTypeCreateSchema(TributeTypeSchema):
    """Same fields; defined to keep explicit naming for OpenAPI in the future."""
    pass
