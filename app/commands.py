"""Flask CLI commands."""

from __future__ import annotations

from datetime import date, time
import secrets

import click
from flask.cli import with_appcontext
from sqlalchemy import func, text

from app.extensions import db
from app.models.appointment import Appointment
from app.models.availability import AppointmentSlot, AvailabilityRule, HolidayOrBlockedDay, Location
from app.models.user import AdminUser, TwoFactorCode, ActivityLog
from app.models.tribute_type import TributeType
from app.models.setting import SystemSetting
from app.services.availability_service import generate_slots_for_rule


DEMO_COMMENT_MARKER = "[seed-demo]"

# ---------------------------------------------------------------------------
# Seed data: Plan 2026 - Contribución Inmobiliaria Urbana y Suburbana
# ---------------------------------------------------------------------------

TRIBUTE_SEED = [
    {
        "name": "Contribución Inmobiliaria Urbana",
        "icon_key": "home",
        "description": "Consulta, regularización y convenios de adeudos de Contribución Inmobiliaria Urbana dentro del Plan 2026.",
        "requirements_text": "Tené a mano un documento de identidad y el número de padrón del inmueble. La oficina podrá solicitar información adicional según el caso.",
        "requires_padron": True,
        "requires_matricula": False,
        "requires_document": True,
        "default_duration_minutes": 30,
        "sort_order": 10,
    },
    {
        "name": "Contribución Inmobiliaria Suburbana",
        "icon_key": "home",
        "description": "Consulta, regularización y convenios de adeudos de Contribución Inmobiliaria Suburbana dentro del Plan 2026.",
        "requirements_text": "Tené a mano un documento de identidad y el número de padrón del inmueble. La oficina podrá solicitar información adicional según el caso.",
        "requires_padron": True,
        "requires_matricula": False,
        "requires_document": True,
        "default_duration_minutes": 30,
        "sort_order": 20,
    },
]

LOCATION_SEED = [
    {
        "name": "Palacio Municipal",
        "address": "Palacio Municipal, Minas, Lavalleja",
        "phone": None,
    },
]

# Absolute dates: 24/07/2026 (Fri) to 31/07/2026 (Fri)
# weekdays: 0=Mon, 2=Wed, 4=Fri
# Expected dates: Fri 24, Mon 27, Wed 29, Fri 31
RULE_SEED = [
    {
        "name": "Agenda demo Plan 2026 - Palacio Municipal",
        "location": "Palacio Municipal",
        "start_date": date(2026, 7, 24),
        "end_date": date(2026, 7, 31),
        "weekdays": [0, 2, 4],
        "start_time": time(9, 0),
        "end_time": time(12, 0),
        "slot_duration_minutes": 30,
        "capacity_per_slot": 2,
        "team": "Hacienda - Plan 2026",
        "applies_to_all": True,
    },
]

APPOINTMENT_DEMO_SEED = [
    {
        "reservation_code": "IDL-AF-2026-DEMO01",
        "tribute_name": "Contribución Inmobiliaria Urbana",
        "target_date": date(2026, 7, 24),
        "target_time": time(9, 0),
        "citizen_name": "Persona Demo Urbana",
        "citizen_document": "1.111.111-1",
        "phone": "099111111",
        "email": "demo.urbana@example.com",
        "reference_value": "10001",
        "comments": f"{DEMO_COMMENT_MARKER} Reserva ficticia para demostración local.",
        "internal_notes": "DATO DE DEMOSTRACIÓN. NO CORRESPONDE A UNA PERSONA REAL.",
        "status": "reserved",
    },
    {
        "reservation_code": "IDL-AF-2026-DEMO02",
        "tribute_name": "Contribución Inmobiliaria Suburbana",
        "target_date": date(2026, 7, 27),
        "target_time": time(10, 0),
        "citizen_name": "Persona Demo Suburbana",
        "citizen_document": "2.222.222-2",
        "phone": "099222222",
        "email": "demo.suburbana@example.com",
        "reference_value": "20002",
        "comments": f"{DEMO_COMMENT_MARKER} Reserva ficticia para demostración local.",
        "internal_notes": "DATO DE DEMOSTRACIÓN. NO CORRESPONDE A UNA PERSONA REAL.",
        "status": "confirmed",
    },
]


# ---------------------------------------------------------------------------
# Settings override for demo
# ---------------------------------------------------------------------------

DEMO_SETTINGS = [
    ("system_name", "Sistema de Agenda – Plan 2026", "string", "Nombre del sistema"),
    ("office_address", "Palacio Municipal, Minas, Lavalleja", "string", "Direccion de la oficina"),
    ("office_hours", "Atención únicamente con agenda previa", "string", "Horario de atencion"),
    ("reservation_code_prefix", "IDL-AF", "string", "Prefijo del codigo de reserva"),
]


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def _cleanup_all_data() -> None:
    """Delete all business data in FK-safe order. Does not touch alembic_version."""
    click.echo("Limpiando datos existentes...")
    db.session.execute(text("DELETE FROM activity_logs"))
    db.session.execute(text("DELETE FROM two_factor_codes"))
    db.session.execute(text("DELETE FROM appointments"))
    db.session.execute(text("DELETE FROM appointment_slots"))
    db.session.execute(text("DELETE FROM availability_rule_tribute_types"))
    db.session.execute(text("DELETE FROM availability_rules"))
    db.session.execute(text("DELETE FROM holidays_or_blocked_days"))
    db.session.execute(text("DELETE FROM tribute_types"))
    db.session.execute(text("DELETE FROM locations"))
    db.session.execute(text("DELETE FROM system_settings"))
    db.session.execute(text("DELETE FROM admin_users"))
    db.session.commit()
    click.echo("Limpieza completa.")


# ---------------------------------------------------------------------------
# Upserts
# ---------------------------------------------------------------------------

def _upsert_tribute(item: dict) -> TributeType:
    tribute = TributeType.query.filter_by(name=item["name"]).first()
    if tribute is None:
        tribute = TributeType(name=item["name"], is_active=True)
        db.session.add(tribute)

    tribute.icon_key = item["icon_key"]
    tribute.slug = None  # let the event listener regenerate
    tribute.description = item["description"]
    tribute.requirements_text = item["requirements_text"]
    tribute.requires_padron = item["requires_padron"]
    tribute.requires_matricula = item["requires_matricula"]
    tribute.requires_document = item["requires_document"]
    tribute.default_duration_minutes = item["default_duration_minutes"]
    tribute.sort_order = item["sort_order"]
    tribute.is_active = True
    return tribute


def _upsert_location(item: dict) -> Location:
    location = Location.query.filter_by(name=item["name"]).first()
    if location is None:
        location = Location(name=item["name"], is_active=True)
        db.session.add(location)

    location.address = item["address"]
    location.phone = item["phone"]
    location.is_active = True
    return location


def _upsert_rule(item: dict, locations_by_name: dict[str, Location]) -> AvailabilityRule:
    with db.session.no_autoflush:
        rule = AvailabilityRule.query.filter_by(name=item["name"]).first()
        if rule is None:
            rule = AvailabilityRule(name=item["name"], is_active=True)
            db.session.add(rule)

        location = locations_by_name[item["location"]]
        rule.name = item["name"]
        rule.location = location
        rule.start_date = item["start_date"]
        rule.end_date = item["end_date"]
        rule.weekdays = item["weekdays"]
        rule.start_time = item["start_time"]
        rule.end_time = item["end_time"]
        rule.slot_duration_minutes = item["slot_duration_minutes"]
        rule.capacity_per_slot = item["capacity_per_slot"]
        rule.team = item["team"]
        rule.applies_to_all = item.get("applies_to_all", False)
        rule.is_active = True
        # Clear tribute_types when applies_to_all is True
        if rule.applies_to_all:
            rule.tribute_types = []
    return rule


def _create_demo_appointments(tributes_by_name: dict[str, TributeType]) -> int:
    created = 0
    for item in APPOINTMENT_DEMO_SEED:
        tribute = tributes_by_name.get(item["tribute_name"])
        if tribute is None:
            click.echo(f"  ADVERTENCIA: tributo '{item['tribute_name']}' no encontrado para reserva demo.")
            continue

        # Find the exact slot
        slot = AppointmentSlot.query.filter_by(
            tribute_type_id=tribute.id,
            date=item["target_date"],
            start_time=item["target_time"],
        ).first()

        if slot is None:
            click.echo(f"  ADVERTENCIA: slot no encontrado para {item['tribute_name']} {item['target_date']} {item['target_time']}")
            continue

        if slot.reserved_count >= slot.capacity:
            click.echo(f"  ADVERTENCIA: slot lleno para {item['tribute_name']} {item['target_date']} {item['target_time']}")
            continue

        # Check for duplicate code
        existing = Appointment.query.filter_by(reservation_code=item["reservation_code"]).first()
        if existing:
            click.echo(f"  ADVERTENCIA: código '{item['reservation_code']}' ya existe, saltando.")
            continue

        appointment = Appointment(
            reservation_code=item["reservation_code"],
            tribute_type_id=tribute.id,
            location_id=slot.location_id,
            slot_id=slot.id,
            citizen_name=item["citizen_name"],
            citizen_document=item["citizen_document"],
            phone=item["phone"],
            email=item["email"],
            reference_value=item["reference_value"],
            comments=item["comments"],
            internal_notes=item["internal_notes"],
            status=item["status"],
        )
        db.session.add(appointment)
        slot.reserved_count = (slot.reserved_count or 0) + 1
        created += 1

    db.session.commit()
    return created


def _apply_demo_settings() -> None:
    for key, value, vtype, desc in DEMO_SETTINGS:
        SystemSetting.set(key, value, vtype, desc)
    db.session.commit()


# ---------------------------------------------------------------------------
# CLI registration
# ---------------------------------------------------------------------------

def register_cli(app):
    app.cli.add_command(create_admin)
    app.cli.add_command(create_bootstrap_admin)
    app.cli.add_command(init_db)
    app.cli.add_command(seed_data)
    app.cli.add_command(reset_admin_password)


@click.command("create-admin")
@click.argument("username")
@click.argument("email")
@click.argument("password")
@click.argument("is_superuser", default="false")
@with_appcontext
def create_admin(username: str, email: str, password: str, is_superuser: str):
    """Crea un usuario administrador."""
    is_super = is_superuser.lower() == "true"

    if AdminUser.query.filter((AdminUser.username == username) | (AdminUser.email == email)).first():
        click.echo("Ya existe un usuario con ese username o email.")
        return

    user = AdminUser(username=username, email=email, is_superuser=is_super, is_active=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    role = "Super Admin" if is_super else "Admin"
    click.echo(f"{role} '{username}' creado correctamente (id={user.id}).")


@click.command("create-bootstrap-admin")
@with_appcontext
def create_bootstrap_admin():
    """Crea el admin inicial desde las variables de entorno BOOTSTRAP_ADMIN_*."""
    from flask import current_app
    username = current_app.config["BOOTSTRAP_ADMIN_USERNAME"]
    email = current_app.config["BOOTSTRAP_ADMIN_EMAIL"]
    password = current_app.config["BOOTSTRAP_ADMIN_PASSWORD"]

    existing = AdminUser.query.filter((AdminUser.username == username) | (AdminUser.email == email)).first()
    if existing:
        click.echo(f"Admin '{username}' ya existe. Use 'flask reset-admin-password' para resetear.")
        return

    user = AdminUser(username=username, email=email, is_superuser=True, is_active=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Admin '{username}' creado. Email: {email}")


@click.command("reset-admin-password")
@click.argument("username")
@click.argument("new_password")
@with_appcontext
def reset_admin_password(username: str, new_password: str):
    user = AdminUser.query.filter_by(username=username).first()
    if not user:
        click.echo("Usuario no encontrado.")
        return
    user.set_password(new_password)
    db.session.commit()
    click.echo(f"Contraseña de '{username}' actualizada.")


@click.command("init-db")
@with_appcontext
def init_db():
    """Crea las tablas que aún no existen."""
    db.create_all()
    click.echo("Tablas creadas/verificadas.")


@click.command("seed-data")
@click.option("--force", is_flag=True, help="Re-poblar incluso si ya hay datos")
@with_appcontext
def seed_data(force: bool):
    """Siembra el escenario demo del Plan 2026: CIU, CIS, Palacio Municipal, 4 días, 48 slots, 2 reservas."""

    # Check if data exists
    existing_tributes = TributeType.query.count()
    existing_locations = Location.query.count()
    existing_rules = AvailabilityRule.query.count()
    existing_slots = AppointmentSlot.query.count()

    has_data = existing_tributes > 0 or existing_locations > 0 or existing_rules > 0

    if has_data and not force:
        click.echo("La base ya contiene datos de negocio.")
        click.echo(f"  Tributos: {existing_tributes}")
        click.echo(f"  Sedes: {existing_locations}")
        click.echo(f"  Reglas: {existing_rules}")
        click.echo(f"  Slots: {existing_slots}")
        click.echo("Usá --force para reconstruir el escenario demo.")
        return

    if force:
        _cleanup_all_data()

    # 1. Ensure defaults + demo settings
    from app.blueprints.admin.settings import ensure_defaults
    ensure_defaults()
    _apply_demo_settings()

    # 2. Tributes
    click.echo("Creando tributos...")
    tributes_by_name: dict[str, TributeType] = {}
    for item in TRIBUTE_SEED:
        tribute = _upsert_tribute(item)
        tributes_by_name[item["name"]] = tribute
    db.session.commit()
    click.echo(f"  Tributos: {TributeType.query.count()}")

    # 3. Locations
    click.echo("Creando sedes...")
    locations_by_name: dict[str, Location] = {}
    for item in LOCATION_SEED:
        location = _upsert_location(item)
        locations_by_name[item["name"]] = location
    db.session.commit()
    click.echo(f"  Sedes: {Location.query.count()}")

    # 4. Rules
    click.echo("Creando reglas de disponibilidad...")
    rules: list[AvailabilityRule] = []
    for item in RULE_SEED:
        rule = _upsert_rule(item, locations_by_name=locations_by_name)
        rules.append(rule)
    db.session.commit()
    click.echo(f"  Reglas: {AvailabilityRule.query.count()}")

    # 5. Generate slots
    click.echo("Generando horarios...")
    generated_slots = 0
    for rule in rules:
        generated_slots += generate_slots_for_rule(rule, overwrite=True)
    click.echo(f"  Slots generados: {generated_slots}")
    click.echo(f"  Slots totales: {AppointmentSlot.query.count()}")

    # 6. Demo appointments
    click.echo("Creando reservas demo...")
    seeded_appointments = _create_demo_appointments(tributes_by_name)
    click.echo(f"  Reservas demo: {seeded_appointments}")

    # 7. Verify no holidays
    holidays_count = HolidayOrBlockedDay.query.count()
    if holidays_count > 0:
        click.echo(f"  ADVERTENCIA: {holidays_count} feriados encontrados (debería ser 0)")

    click.echo("")
    click.echo("Seed demo Plan 2026 completo.")
    click.echo(f"  Tributos: {TributeType.query.count()}")
    click.echo(f"  Sedes: {Location.query.count()}")
    click.echo(f"  Reglas: {AvailabilityRule.query.count()}")
    click.echo(f"  Slots: {AppointmentSlot.query.count()}")
    click.echo(f"  Reservas: {Appointment.query.count()}")
    click.echo(f"  Feriados: {holidays_count}")
