"""Operational ticket service for the admin dashboard.

Centralizes:
- America/Montevideo "today" and "current hour" resolution;
- allowed status transitions;
- state changes with immutable audit events;
- day summary metrics.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import func

from app.extensions import db
from app.models.appointment import Appointment
from app.models.availability import AppointmentSlot
from app.models.ticket_event import TicketEvent
from app.models.tribute_type import TributeType
from app.utils.logging_helper import log_activity

MONTEVIDEO = ZoneInfo("America/Montevideo")

# ---------------------------------------------------------------------------
# Zone helpers
# ---------------------------------------------------------------------------

def today_uy() -> object:
    return datetime.now(MONTEVIDEO).date()


def current_hour_uy() -> int:
    return datetime.now(MONTEVIDEO).hour


def current_time_uy() -> datetime:
    return datetime.now(MONTEVIDEO)


# ---------------------------------------------------------------------------
# Status model
# ---------------------------------------------------------------------------

# Backend stores: reserved, confirmed, called, in_service, attended, resolved,
# cancelled, no_show. The dashboard maps reserved/confirmed to the visible
# "pending" bucket while keeping the exact stored value untouched.
PENDING_STATUSES = ("reserved", "confirmed")
OPERATIONAL_STATUSES = ("called", "in_service", "attended", "resolved", "cancelled", "no_show")

# Allowed transitions from each stored status. Terminal states have no outgoing
# transitions unless explicitly reopened by an operator with permission.
TICKET_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "reserved": ("called", "cancelled"),
    "confirmed": ("called", "cancelled"),
    "called": ("in_service", "no_show", "reserved", "cancelled"),
    "in_service": ("attended", "resolved", "reserved", "cancelled"),
    "attended": ("resolved",),
    "resolved": (),
    "cancelled": (),
    "no_show": ("reserved", "called"),
}


def get_allowed_transitions(status: str | None) -> list[str]:
    return list(TICKET_TRANSITIONS.get(status or "reserved", ()))


def can_transition(from_status: str | None, to_status: str | None) -> bool:
    return to_status in TICKET_TRANSITIONS.get(from_status or "reserved", ())


def bucket_of(status: str | None) -> str:
    """Map stored status to a dashboard bucket."""
    if status in PENDING_STATUSES:
        return "pending"
    return status or "pending"


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

def record_ticket_event(
    appointment: Appointment,
    *,
    to_status: str,
    from_status: str | None = None,
    user=None,
    note: str | None = None,
) -> TicketEvent:
    event = TicketEvent(
        appointment_id=appointment.id,
        from_status=from_status,
        to_status=to_status,
        user_id=getattr(user, "id", None),
        username=getattr(user, "username", None),
        note=note,
    )
    db.session.add(event)
    return event


def change_ticket_status(
    appointment: Appointment,
    to_status: str,
    *,
    user=None,
    note: str | None = None,
) -> Appointment:
    """Validate and apply a status change, writing an immutable audit event."""
    from_status = appointment.status
    if to_status == from_status:
        return appointment
    if not can_transition(from_status, to_status):
        raise ValueError(f"Transición inválida de {from_status} a {to_status}")

    appointment.status = to_status
    record_ticket_event(appointment, to_status=to_status, from_status=from_status, user=user, note=note)
    db.session.commit()
    log_activity(
        "TICKET_STATUS_CHANGE",
        f"Ticket {appointment.reservation_code}: {from_status} -> {to_status}",
        user=user,
    )
    return appointment


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def _slot_dated_base(date_value):
    return (
        Appointment.query
        .join(AppointmentSlot, Appointment.slot_id == AppointmentSlot.id)
        .filter(AppointmentSlot.date == date_value)
    )


def list_today_tickets(
    *,
    date_value=None,
    hour: int | None = None,
    status: str | None = None,
    service_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[dict], int]:
    date_value = date_value or today_uy()
    q = _slot_dated_base(date_value)

    if hour is not None:
        start = time(hour, 0, 0)
        end = time(hour, 59, 59) if hour < 23 else time(23, 59, 59)
        q = q.filter(AppointmentSlot.start_time >= start, AppointmentSlot.start_time <= end)
    if status:
        q = q.filter(Appointment.status == status)
    if service_id:
        q = q.filter(Appointment.tribute_type_id == service_id)
    if search:
        term = f"%{search.strip()}%"
        from sqlalchemy import or_
        q = q.filter(or_(
            Appointment.citizen_name.ilike(term),
            Appointment.reservation_code.ilike(term),
        ))

    total = q.count()
    rows = (
        q.order_by(
            AppointmentSlot.start_time.asc(),
            Appointment.created_at.asc(),
            Appointment.reservation_code.asc(),
        )
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return [serialize_ticket(r) for r in rows], total


def serialize_ticket(appointment: Appointment) -> dict:
    slot = appointment.slot
    tribute = appointment.tribute_type
    location = appointment.location
    return {
        "id": appointment.id,
        "code": appointment.reservation_code,
        "status": appointment.status,
        "bucket": bucket_of(appointment.status),
        "person_name": appointment.citizen_name,
        "scheduled_time": slot.start_time.strftime("%H:%M") if slot and slot.start_time else None,
        "registered_at": appointment.created_at.isoformat() if appointment.created_at else None,
        "updated_at": appointment.updated_at.isoformat() if appointment.updated_at else None,
        "service": {
            "id": tribute.id,
            "name": tribute.name,
            "icon_key": tribute.icon_key or "document",
        } if tribute else None,
        "desk": location.name if location else None,
        "comment": appointment.comments or "",
        "internal_notes": appointment.internal_notes or "",
    }


def get_ticket(appointment_id: int) -> Optional[dict]:
    appointment = db.session.get(Appointment, appointment_id)
    return serialize_ticket(appointment) if appointment else None


def get_ticket_history(appointment_id: int) -> list[dict]:
    events = (
        TicketEvent.query
        .filter_by(appointment_id=appointment_id)
        .order_by(TicketEvent.created_at.asc(), TicketEvent.id.asc())
        .all()
    )
    return [event.to_dict() for event in events]


def current_hour_snapshot(*, date_value=None, hour: int | None = None) -> dict:
    """Tickets for the current (or requested) hour plus the ticket currently called."""
    date_value = date_value or today_uy()
    hour = hour if hour is not None else current_hour_uy()
    tickets, _total = list_today_tickets(date_value=date_value, hour=hour, per_page=200)
    called = next((t for t in tickets if t["status"] == "called"), None)
    return {
        "date": date_value.isoformat(),
        "hour": hour,
        "called_ticket": called,
        "tickets": tickets,
        "updated_at": current_time_uy().isoformat(),
    }


def day_summary(*, date_value=None) -> dict:
    """Operational summary of the day used by the dashboard overview."""
    date_value = date_value or today_uy()
    rows = _slot_dated_base(date_value).all()

    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1

    bucket_counts = {
        "pending": sum(status_counts.get(s, 0) for s in PENDING_STATUSES),
        "called": status_counts.get("called", 0),
        "in_service": status_counts.get("in_service", 0),
        "attended": status_counts.get("attended", 0),
        "resolved": status_counts.get("resolved", 0),
        "no_show": status_counts.get("no_show", 0),
        "cancelled": status_counts.get("cancelled", 0),
    }

    hour = current_hour_uy()
    start = time(hour, 0, 0)
    end = time(23, 59, 59) if hour == 23 else time(hour, 59, 59)
    current_hour_rows = [r for r in rows if r.slot and start <= r.slot.start_time <= end]
    active = ("reserved", "confirmed", "called", "in_service")
    current_hour_count = sum(1 for r in current_hour_rows if r.status in active)

    next_pending = next(
        (
            serialize_ticket(r)
            for r in rows
            if r.status in PENDING_STATUSES and r.slot
        ),
        None,
    )

    # Per-hour distribution of scheduled times.
    by_hour: dict[int, int] = {}
    for r in rows:
        if r.slot and r.slot.start_time:
            by_hour[r.slot.start_time.hour] = by_hour.get(r.slot.start_time.hour, 0) + 1

    # Volume by service.
    by_service: dict[str, int] = {}
    for r in rows:
        name = (r.tribute_type.name if r.tribute_type else "Sin servicio") or "Sin servicio"
        by_service[name] = by_service.get(name, 0) + 1

    # Resolution metrics.
    total = len(rows)
    resolved = status_counts.get("resolved", 0) + status_counts.get("attended", 0)
    resolution_rate = round(resolved / total * 100, 1) if total else 0

    # Average wait (registration -> called) and attention (called -> resolved/attended)
    # computed from the immutable event trail.
    wait_times: list[float] = []
    attention_times: list[float] = []
    for r in rows:
        events = (
            TicketEvent.query
            .filter_by(appointment_id=r.id)
            .order_by(TicketEvent.created_at.asc())
            .all()
        )
        registered = r.created_at
        called_at = next((e.created_at for e in events if e.to_status == "called"), None)
        if registered and called_at:
            wait_times.append((called_at - registered).total_seconds() / 60)
        closed_at = next(
            (e.created_at for e in events if e.to_status in ("resolved", "attended")),
            None,
        )
        if called_at and closed_at:
            attention_times.append((closed_at - called_at).total_seconds() / 60)

    def _avg(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 1) if values else None

    return {
        "date": date_value.isoformat(),
        "total": total,
        "buckets": bucket_counts,
        "current_hour": {
            "hour": hour,
            "count": current_hour_count,
        },
        "next_pending": next_pending,
        "avg_wait_minutes": _avg(wait_times),
        "avg_attention_minutes": _avg(attention_times),
        "resolution_rate": resolution_rate,
        "by_hour": [{"hour": h, "count": c} for h, c in sorted(by_hour.items())],
        "by_service": [{"service": name, "count": c} for name, c in sorted(by_service.items(), key=lambda kv: -kv[1])],
        "top_service": max(by_service, key=by_service.get) if by_service else None,
        "updated_at": current_time_uy().isoformat(),
    }
