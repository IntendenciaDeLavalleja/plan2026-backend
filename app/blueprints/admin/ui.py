from __future__ import annotations

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

admin_ui_bp = Blueprint("admin_ui", __name__)


def _admin_nav(active: str):
    nav = [
        {"label": "Panel", "href": "/admin", "active": active == "dashboard"},
        {"label": "Turnos", "href": "/admin/turnos", "active": active == "appointments"},
        {"label": "Disponibilidad", "href": "/admin/disponibilidad", "active": active == "availability"},
        {"label": "Tributos", "href": "/admin/tributos", "active": active == "tributes"},
        {"label": "Sedes", "href": "/admin/sedes", "active": active == "locations"},
    ]
    if current_user.is_superuser:
        nav.extend([
            {"label": "Usuarios", "href": "/admin/usuarios", "active": active == "users"},
            {"label": "Logs del sistema", "href": "/admin/logs", "active": active == "logs"},
        ])
    return nav


@admin_ui_bp.get("/admin/login")
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("admin_ui.dashboard_page"))
    return render_template("admin/login.html")


@admin_ui_bp.get("/admin")
@login_required
def dashboard_page():
    return render_template("admin/dashboard.html", user=current_user, nav_items=_admin_nav("dashboard"))


@admin_ui_bp.get("/admin/tributos")
@login_required
def tribute_types_page():
    return render_template("admin/tribute_types.html", user=current_user, nav_items=_admin_nav("tributes"))


@admin_ui_bp.get("/admin/disponibilidad")
@login_required
def availability_page():
    return render_template("admin/availability.html", user=current_user, nav_items=_admin_nav("availability"))


@admin_ui_bp.get("/admin/turnos")
@login_required
def appointments_page():
    return render_template("admin/appointments.html", user=current_user, nav_items=_admin_nav("appointments"))


@admin_ui_bp.get("/admin/registrar-turno")
@login_required
def appointment_create_page():
    return render_template("admin/appointment_create.html", user=current_user, nav_items=_admin_nav("appointments"))


@admin_ui_bp.get("/admin/sedes")
@login_required
def locations_page():
    return render_template("admin/locations.html", user=current_user, nav_items=_admin_nav("locations"))



@admin_ui_bp.get("/admin/usuarios")
@login_required
def users_page():
    if not current_user.is_superuser:
        return redirect(url_for("admin_ui.dashboard_page"))
    return render_template("admin/users.html", user=current_user, nav_items=_admin_nav("users"))


@admin_ui_bp.get("/admin/logs")
@login_required
def logs_page():
    if not current_user.is_superuser:
        return redirect(url_for("admin_ui.dashboard_page"))
    return render_template("admin/logs.html", user=current_user, nav_items=_admin_nav("logs"))
