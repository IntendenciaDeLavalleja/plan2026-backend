"""JWT dashboard data adapters sharing the existing ticket service."""

from flask import Blueprint, request

from app.extensions import db
from app.models.appointment import Appointment
from app.services import ticket_service
from app.utils.dashboard_jwt import current_dashboard_admin, jwt_admin_required
from app.utils.responses import fail, ok, paginated

dashboard_api_bp = Blueprint("dashboard_api", __name__)


@dashboard_api_bp.get("/dashboard/today")
@jwt_admin_required
def today():
    return ok(ticket_service.day_summary())


@dashboard_api_bp.get("/tickets/current-hour")
@jwt_admin_required
def current_hour():
    return ok(ticket_service.current_hour_snapshot())


@dashboard_api_bp.get("/tickets")
@jwt_admin_required
def list_tickets():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 50, type=int), 1), 200)
    items, total = ticket_service.list_today_tickets(hour=request.args.get("hour", type=int), status=request.args.get("status"), service_id=request.args.get("service_id", type=int), search=request.args.get("search"), page=page, per_page=per_page)
    return ok(paginated(items, page, per_page, total))


@dashboard_api_bp.get("/tickets/<int:ticket_id>")
@jwt_admin_required
def ticket(ticket_id: int):
    item = ticket_service.get_ticket(ticket_id)
    return ok(item) if item else fail("Ticket no encontrado", 404, code="not_found")


@dashboard_api_bp.get("/tickets/<int:ticket_id>/history")
@jwt_admin_required
def ticket_history(ticket_id: int):
    if not db.session.get(Appointment, ticket_id):
        return fail("Ticket no encontrado", 404, code="not_found")
    return ok(ticket_service.get_ticket_history(ticket_id))


@dashboard_api_bp.patch("/tickets/<int:ticket_id>/status")
@jwt_admin_required
def change_ticket_status(ticket_id: int):
    appointment = db.session.get(Appointment, ticket_id)
    if not appointment:
        return fail("Ticket no encontrado", 404, code="not_found")
    body = request.get_json(silent=True) or {}
    status = (body.get("status") or "").strip()
    if not status:
        return fail("status es requerido", 400, code="missing_status")
    try:
        updated = ticket_service.change_ticket_status(appointment, status, user=current_dashboard_admin(), note=(body.get("note") or "").strip() or None)
    except ValueError as exc:
        return fail(str(exc), 400, code="invalid_transition")
    return ok(ticket_service.serialize_ticket(updated))
