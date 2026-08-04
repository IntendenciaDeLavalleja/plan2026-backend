import os
from flask import Flask, jsonify, redirect, request, url_for
from flask_login import current_user

from .config import Config
from .extensions import db, migrate, login_manager, mail, ma, limiter, talisman, csrf, cors, jwt


def _unauthorized():
    return jsonify({"error": "unauthorized", "message": "Autenticación requerida"}), 401


def _forbidden():
    return jsonify({"error": "forbidden", "message": "No tiene permisos para realizar esta acción"}), 403


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # CORS – only the configured frontend origin(s) can call our JSON API
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=False,
        allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Requested-With"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    ma.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)
    jwt.init_app(app)
    # Talisman is opt-in for production. Disabled by default for dev convenience.
    # talisman.init_app(app, content_security_policy=app.config.get('CSP'))

    # User loader for Flask-Login (admin users)
    from .models.user import AdminUser

    @login_manager.user_loader
    def _load_user(user_id):
        try:
            return db.session.get(AdminUser, int(user_id))
        except (TypeError, ValueError):
            return None

    @login_manager.unauthorized_handler
    def _on_unauthorized():
        if request.path.startswith("/api/"):
            return _unauthorized()
        return redirect(url_for("admin_ui.login_page"))

    @jwt.unauthorized_loader
    def _jwt_unauthorized(_reason):
        return _unauthorized()

    @jwt.invalid_token_loader
    def _jwt_invalid(_reason):
        return _unauthorized()

    @jwt.expired_token_loader
    def _jwt_expired(_header, _payload):
        return _unauthorized()

    # Register error handlers for clean JSON
    from .utils.responses import register_error_handlers

    register_error_handlers(app)

    # Register blueprints
    from .blueprints.public.routes import public_bp
    from .blueprints.admin.auth import admin_auth_bp
    from .blueprints.admin.dashboard import admin_dashboard_bp
    from .blueprints.admin.tribute_types import admin_tribute_types_bp
    from .blueprints.admin.availability import admin_availability_bp
    from .blueprints.admin.appointments import admin_appointments_bp
    from .blueprints.admin.settings import admin_settings_bp
    from .blueprints.admin.locations import admin_locations_bp
    from .blueprints.admin.ui import admin_ui_bp
    from .blueprints.admin.panel_auth import panel_auth_bp

    csrf.exempt(public_bp)
    csrf.exempt(admin_auth_bp)
    csrf.exempt(admin_dashboard_bp)
    csrf.exempt(admin_tribute_types_bp)
    csrf.exempt(admin_availability_bp)
    csrf.exempt(admin_appointments_bp)
    csrf.exempt(admin_settings_bp)
    csrf.exempt(admin_locations_bp)
    csrf.exempt(admin_ui_bp)

    app.register_blueprint(public_bp, url_prefix="/api/public")
    app.register_blueprint(admin_auth_bp, url_prefix="/api/admin/auth")
    app.register_blueprint(admin_dashboard_bp, url_prefix="/api/admin")
    app.register_blueprint(admin_tribute_types_bp, url_prefix="/api/admin/tribute-types")
    app.register_blueprint(admin_availability_bp, url_prefix="/api/admin/availability")
    app.register_blueprint(admin_appointments_bp, url_prefix="/api/admin/appointments")
    app.register_blueprint(admin_settings_bp, url_prefix="/api/admin/settings")
    app.register_blueprint(admin_locations_bp, url_prefix="/api/admin/locations")
    app.register_blueprint(admin_ui_bp)
    app.register_blueprint(panel_auth_bp)

    # Register CLI commands
    from .commands import register_cli

    register_cli(app)

    # Import models so SQLAlchemy registers them
    from . import models  # noqa: F401

    return app


__all__ = ["create_app"]
