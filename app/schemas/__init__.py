"""Marshmallow schemas for the API."""

from .tribute_type_schema import TributeTypeSchema, TributeTypeCreateSchema
from .availability_schema import (
    AvailabilityRuleSchema,
    AvailabilityRuleCreateSchema,
    AppointmentSlotSchema,
    HolidaySchema,
    LocationSchema,
    LocationCreateSchema,
)
from .appointment_schema import (
    AppointmentCreateSchema,
    AppointmentAdminSchema,
    AppointmentPublicSchema,
)

__all__ = [
    "TributeTypeSchema",
    "TributeTypeCreateSchema",
    "AvailabilityRuleSchema",
    "AvailabilityRuleCreateSchema",
    "AppointmentSlotSchema",
    "HolidaySchema",
    "LocationSchema",
    "LocationCreateSchema",
    "AppointmentCreateSchema",
    "AppointmentAdminSchema",
    "AppointmentPublicSchema",
]
