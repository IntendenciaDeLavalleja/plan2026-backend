"""Admin operational tickets API for the dashboard app."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models.appointment import Appointment
from app.services import ticket_service
from app.utils.responses import fail, ok, paginated

admin_tickets_bp = Blueprint("admin_tickets", __name__)


@admin_tickets_bp.get("")
@login_required
def list_tickets():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 50, type=int), 1), 200)
    hour = request.args.get("hour", type=int)
    status = request.args.get("status") or None
    service_id = request.args.get("service_id", type=int)
    search = request.args.get("search") or None

    items, total = ticket_service.list_today_tickets(
        hour=hour,
        status=status,
        service_id=service_id,
        search=search,
        page=page,
        per_page=per_page,
    )
    return ok(paginated(items, page, per_page, total))


@admin_tickets_bp.get("/current-hour")
@login_required
def current_hour():
    return ok(ticket_service.current_hour_snapshot())


@admin_tickets_bp.get("/<int:ticket_id>")
@login_required
def get_ticket(ticket_id: int):
    ticket = ticket_service.get_ticket(ticket_id)
    if not ticket:
        return fail("Ticket no encontrado", 404, code="not_found")
    return ok(ticket)


@admin_tickets_bp.get("/<int:ticket_id>/history")
@login_required
def get_ticket_history(ticket_id: int):
    if not db.session.get(Appointment, ticket_id):
        return fail("Ticket no encontrado", 404, code="not_found")
    return ok(ticket_service.get_ticket_history(ticket_id))


@admin_tickets_bp.patch("/<int:ticket_id>/status")
@login_required
def change_status(ticket_id: int):
    appointment = db.session.get(Appointment, ticket_id)
    if not appointment:
        return fail("Ticket no encontrado", 404, code="not_found")

    body = request.get_json(silent=True) or {}
    to_status = (body.get("status") or "").strip()
    note = (body.get("note") or "").strip() or None
    if not to_status:
        return fail("status es requerido", 400, code="missing_status")

    try:
        updated = ticket_service.change_ticket_status(
            appointment,
            to_status,
            user=current_user,
            note=note,
        )
    except ValueError as exc:
        return fail(str(exc), 400, code="invalid_transition")

    return ok(ticket_service.serialize_ticket(updated))
