from datetime import date, time

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.availability import AppointmentSlot, AvailabilityRule, Location
from app.models.tribute_type import TributeType
from app.services.availability_service import bulk_generate_slots


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    RATELIMIT_STORAGE_URI = "memory://"
    WTF_CSRF_ENABLED = False


def _generate(*, capacity=1, overwrite=False):
    return bulk_generate_slots(
        start_date=date(2026, 8, 31),
        end_date=date(2026, 8, 31),
        weekdays=[0],
        start_time=time(9, 0),
        end_time=time(10, 0),
        duration_minutes=60,
        capacity=capacity,
        location_id=1,
        tribute_type_ids=None,
        applies_to_all=True,
        overwrite=overwrite,
    )


def test_bulk_generation_reports_duplicates_and_updates_explicitly():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        db.session.add(Location(id=1, name="Palacio Municipal"))
        db.session.add_all([
            TributeType(name="Contribución Urbana", slug="urbana", is_active=True),
            TributeType(name="Contribución Sub Urbana", slug="suburbana", is_active=True),
        ])
        db.session.commit()

        assert _generate() == {
            "created_slots": 2,
            "updated_slots": 0,
            "skipped_slots": 0,
        }
        assert AppointmentSlot.query.count() == 2
        assert AvailabilityRule.query.count() == 1

        assert _generate() == {
            "created_slots": 0,
            "updated_slots": 0,
            "skipped_slots": 2,
        }
        assert AppointmentSlot.query.count() == 2
        assert AvailabilityRule.query.count() == 1

        assert _generate(capacity=3, overwrite=True) == {
            "created_slots": 0,
            "updated_slots": 2,
            "skipped_slots": 0,
        }
        assert {slot.capacity for slot in AppointmentSlot.query.all()} == {3}
        assert AvailabilityRule.query.count() == 2

        db.session.remove()
        db.drop_all()


def test_overwrite_never_reduces_capacity_below_reservations():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        db.session.add(Location(id=1, name="Palacio Municipal"))
        db.session.add(TributeType(name="Contribución Urbana", slug="urbana", is_active=True))
        db.session.commit()

        _generate(capacity=5)
        slot = AppointmentSlot.query.one()
        slot.reserved_count = 4
        db.session.commit()

        result = _generate(capacity=1, overwrite=True)
        assert result["updated_slots"] == 1
        assert AppointmentSlot.query.one().capacity == 4

        db.session.remove()
        db.drop_all()
