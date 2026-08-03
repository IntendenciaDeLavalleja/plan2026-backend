"""Availability + slot generation logic."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable, Optional

from flask import current_app
from sqlalchemy import and_, or_

from app.extensions import db
from app.models.availability import (
    AppointmentSlot,
    AvailabilityRule,
    HolidayOrBlockedDay,
    Location,
)
from app.models.appointment import Appointment
from app.models.tribute_type import TributeType


WEEKDAY_LABELS = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slot_datetimes_for_rule(rule: AvailabilityRule, target_date: date) -> Iterable[tuple[time, time]]:
    """Yield (start_time, end_time) tuples for a given date following the rule."""
    duration = timedelta(minutes=rule.slot_duration_minutes)
    cursor = datetime.combine(target_date, rule.start_time)
    end_of_day = datetime.combine(target_date, rule.end_time)
    while cursor + duration <= end_of_day:
        start_t = cursor.time()
        end_t = (cursor + duration).time()
        yield start_t, end_t
        cursor += duration


def _is_blocked_date(target_date: date) -> Optional[HolidayOrBlockedDay]:
    return HolidayOrBlockedDay.query.filter_by(date=target_date).first()


def is_date_blocked(target_date: date) -> bool:
    return _is_blocked_date(target_date) is not None


# ---------------------------------------------------------------------------
# Slot generation
# ---------------------------------------------------------------------------

def generate_slots_for_rule(rule: AvailabilityRule, overwrite: bool = False) -> int:
    """Materialize slots for a single rule. Returns number of slots created/updated."""
    if not rule.is_active:
        return 0
    if rule.end_date < rule.start_date:
        return 0

    weekdays = set(rule.weekdays or [])
    tribute_ids: list[int]
    if rule.applies_to_all:
        tribute_ids = [t.id for t in TributeType.query.filter_by(is_active=True).all()]
    else:
        tribute_ids = [t.id for t in rule.tribute_types if t.is_active]

    if not tribute_ids:
        return 0

    created = 0
    cursor = rule.start_date
    while cursor <= rule.end_date:
        # weekday(): Mon=0..Sun=6 — matches the convention used in the rule
        if cursor.weekday() in weekdays and _is_blocked_date(cursor) is None:
            for start_t, end_t in _slot_datetimes_for_rule(rule, cursor):
                for tid in tribute_ids:
                    existing = AppointmentSlot.query.filter_by(
                        tribute_type_id=tid,
                        location_id=rule.location_id,
                        date=cursor,
                        start_time=start_t,
                    ).first()
                    if existing:
                        if overwrite:
                            existing.end_time = end_t
                            existing.capacity = rule.capacity_per_slot
                            existing.rule_id = rule.id
                        continue
                    slot = AppointmentSlot(
                        tribute_type_id=tid,
                        location_id=rule.location_id,
                        rule_id=rule.id,
                        date=cursor,
                        start_time=start_t,
                        end_time=end_t,
                        capacity=rule.capacity_per_slot,
                    )
                    db.session.add(slot)
                    created += 1
        cursor += timedelta(days=1)
    if created:
        db.session.commit()
    return created


def bulk_generate_slots(
    *,
    start_date: date,
    end_date: date,
    weekdays: list[int],
    start_time: time,
    end_time: time,
    duration_minutes: int,
    capacity: int,
    location_id: int | None,
    tribute_type_ids: list[int] | None,
    applies_to_all: bool = False,
    overwrite: bool = False,
) -> int:
    """Ad-hoc slot generation used by the admin endpoint."""
    rule = AvailabilityRule(
        name="Generación rápida",
        start_date=start_date,
        end_date=end_date,
        weekdays=weekdays,
        start_time=start_time,
        end_time=end_time,
        slot_duration_minutes=duration_minutes,
        capacity_per_slot=capacity,
        location_id=location_id,
        applies_to_all=applies_to_all,
        is_active=True,
    )
    if applies_to_all or not tribute_type_ids:
        rule.applies_to_all = True
    else:
        rule.tribute_types = TributeType.query.filter(TributeType.id.in_(tribute_type_ids)).all()
    db.session.add(rule)
    db.session.flush()
    created = generate_slots_for_rule(rule, overwrite=overwrite)
    return created


# ---------------------------------------------------------------------------
# Read helpers (used by the public endpoints)
# ---------------------------------------------------------------------------

def list_available_dates(
    tribute_type_id: int,
    *,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: int = 60,
) -> list[dict]:
    """Return a list of dates with available slots for the given tribute type."""
    from_date = from_date or date.today()
    to_date = to_date or (from_date + timedelta(days=60))

    rows = (
        AppointmentSlot.query.filter(
            AppointmentSlot.tribute_type_id == tribute_type_id,
            AppointmentSlot.is_blocked.is_(False),
            AppointmentSlot.reserved_count < AppointmentSlot.capacity,
            AppointmentSlot.date >= from_date,
            AppointmentSlot.date <= to_date,
        )
        .order_by(AppointmentSlot.date.asc(), AppointmentSlot.start_time.asc())
        .all()
    )

    # Filter out holidays explicitly
    blocked = {h.date for h in HolidayOrBlockedDay.query.filter(
        HolidayOrBlockedDay.date >= from_date, HolidayOrBlockedDay.date <= to_date).all()}

    min_start = datetime.now() + timedelta(hours=current_app.config["MIN_ANTICIPATION_HOURS"])
    max_start = datetime.now() + timedelta(days=current_app.config["MAX_ANTICIPATION_DAYS"])
    dates: dict[date, int] = {}
    for slot in rows:
        if slot.date in blocked:
            continue
        start = datetime.combine(slot.date, slot.start_time)
        if start < min_start or start > max_start:
            continue
        dates[slot.date] = dates.get(slot.date, 0) + slot.remaining

    out: list[dict] = []
    for d, remaining in dates.items():
        out.append({
            "date": d.isoformat(),
            "remaining": remaining,
            "weekday": WEEKDAY_LABELS.get(d.weekday(), ""),
        })
    return out[:limit]


def list_available_slots(tribute_type_id: int, target_date: date) -> list[dict]:
    """Return available slots for a specific date + tribute type."""
    if _is_blocked_date(target_date):
        return []
    q = (
        AppointmentSlot.query
        .filter(
            AppointmentSlot.tribute_type_id == tribute_type_id,
            AppointmentSlot.date == target_date,
            AppointmentSlot.is_blocked.is_(False),
            AppointmentSlot.reserved_count < AppointmentSlot.capacity,
        )
        .order_by(AppointmentSlot.start_time.asc())
    )
    min_start = datetime.now() + timedelta(hours=current_app.config["MIN_ANTICIPATION_HOURS"])
    max_start = datetime.now() + timedelta(days=current_app.config["MAX_ANTICIPATION_DAYS"])
    rows = [
        slot for slot in q.all()
        if min_start <= datetime.combine(slot.date, slot.start_time) <= max_start
    ]
    return [r.to_dict() for r in rows]


def get_availability_for_tribute_type(tribute_type_id: int, days: int = 14) -> dict:
    """High level helper used by the home page."""
    from_date = date.today()
    to_date = from_date + timedelta(days=days)
    return {
        "tribute_type_id": tribute_type_id,
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "dates": list_available_dates(tribute_type_id, from_date=from_date, to_date=to_date),
    }


def get_location_name(location_id: int | None) -> str | None:
    if not location_id:
        return None
    loc = db.session.get(Location, location_id)
    return loc.name if loc else None
