from __future__ import annotations

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required, logout_user

admin_ui_bp = Blueprint("admin_ui", __name__)


def _admin_nav(active: str):
    return [
        {"label": "Panel", "href": "/admin", "active": active == "dashboard"},
        {"label": "Turnos", "href": "/admin/turnos", "active": active == "appointments"},
        {"label": "Disponibilidad", "href": "/admin/disponibilidad", "active": active == "availability"},
        {"label": "Tributos", "href": "/admin/tributos", "active": active == "tributes"},
        {"label": "Sedes", "href": "/admin/sedes", "active": active == "locations"},
        {"label": "Configuración", "href": "/admin/configuracion", "active": active == "settings"},
    ]


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


@admin_ui_bp.get("/admin/configuracion")
@login_required
def settings_page():
    return render_template("admin/settings.html", user=current_user, nav_items=_admin_nav("settings"))


@admin_ui_bp.get("/admin/logout")
@login_required
def logout_page():
    logout_user()
    return redirect(url_for("admin_ui.login_page"))
