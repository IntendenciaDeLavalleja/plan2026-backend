"""Admin API blueprints package.

Each sub-module exposes a Blueprint named ``<name>_bp`` that is imported here
so they can be registered by the application factory.
"""

from flask import Blueprint

# Defined in submodules (kept here to ensure they are imported once)
from .auth import admin_auth_bp  # noqa: F401
from .dashboard import admin_dashboard_bp  # noqa: F401
from .tribute_types import admin_tribute_types_bp  # noqa: F401
from .availability import admin_availability_bp  # noqa: F401
from .appointments import admin_appointments_bp  # noqa: F401
from .locations import admin_locations_bp  # noqa: F401
