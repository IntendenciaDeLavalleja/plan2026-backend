"""Admin dashboard: aggregate counts + next appointments."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from flask import Blueprint
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models.appointment import Appointment
from app.models.availability import AppointmentSlot, HolidayOrBlockedDay
from app.models.tribute_type import TributeType
from app.utils.responses import ok, paginated

admin_dashboard_bp = Blueprint("admin_dashboard", __name__)


@admin_dashboard_bp.get("/dashboard")
@login_required
def dashboard():
    today = date.today()
    end_of_week = today + timedelta(days=7)

    appt_by_status = dict(
        db.session.query(Appointment.status, func.count(Appointment.id))
        .group_by(Appointment.status)
        .all()
    )

    today_count = (
        db.session.query(func.count(Appointment.id))
        .join(AppointmentSlot, Appointment.slot_id == AppointmentSlot.id)
        .filter(AppointmentSlot.date == today)
        .filter(Appointment.status.in_(("reserved", "confirmed")))
        .scalar()
        or 0
    )

    upcoming = (
        db.session.query(func.count(Appointment.id))
        .join(AppointmentSlot, Appointment.slot_id == AppointmentSlot.id)
        .filter(AppointmentSlot.date >= today)
        .filter(Appointment.status.in_(("reserved", "confirmed")))
        .scalar()
        or 0
    )

    pending = (
        db.session.query(func.count(Appointment.id))
        .filter(Appointment.status == "reserved")
        .scalar()
        or 0
    )

    cancelled = appt_by_status.get("cancelled", 0)

    weekly_capacity = (
        db.session.query(func.coalesce(func.sum(AppointmentSlot.capacity - AppointmentSlot.reserved_count), 0))
        .filter(AppointmentSlot.date >= today)
        .filter(AppointmentSlot.date <= end_of_week)
        .filter(AppointmentSlot.is_blocked.is_(False))
        .scalar()
        or 0
    )

    active_tributes = (
        db.session.query(func.count(TributeType.id))
        .filter(TributeType.is_active.is_(True))
        .scalar()
        or 0
    )

    # Next 8 upcoming appointments
    next_rows = (
        Appointment.query
        .join(AppointmentSlot, Appointment.slot_id == AppointmentSlot.id)
        .filter(AppointmentSlot.date >= today)
        .filter(Appointment.status.in_(("reserved", "confirmed")))
        .order_by(AppointmentSlot.date.asc(), AppointmentSlot.start_time.asc())
        .limit(8)
        .all()
    )

    return ok({
        "metrics": {
            "today": int(today_count),
            "upcoming": int(upcoming),
            "pending": int(pending),
            "cancelled": int(cancelled),
            "weekly_capacity": int(weekly_capacity),
            "active_tributes": int(active_tributes),
            "no_show": int(appt_by_status.get("no_show", 0)),
            "attended": int(appt_by_status.get("attended", 0)),
            "confirmed": int(appt_by_status.get("confirmed", 0)),
        },
        "upcoming_appointments": [a.to_admin_dict() for a in next_rows],
    })


@admin_dashboard_bp.get("/health")
@login_required
def health():
    return ok({
        "status": "ok",
        "now": datetime.now(timezone.utc).isoformat(),
    })
