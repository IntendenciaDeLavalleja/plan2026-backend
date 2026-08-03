"""Initial migration for Amnistia Financiera

Revision ID: 8f4d2a9e3c12
Revises:
Create Date: 2026-06-03 00:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "8f4d2a9e3c12"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(120), nullable=False, unique=True),
        sa.Column("full_name", sa.String(120), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "two_factor_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("purpose", sa.String(40), nullable=False, server_default="login"),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(60), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "tribute_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(180), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon_key", sa.String(80), nullable=True),
        sa.Column("requirements_text", sa.Text(), nullable=True),
        sa.Column("default_duration_minutes", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("requires_padron", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requires_matricula", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requires_document", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tribute_types_slug", "tribute_types", ["slug"], unique=True)

    op.create_table(
        "availability_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("weekdays", sa.JSON(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("slot_duration_minutes", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("capacity_per_slot", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("team", sa.String(120), nullable=True),
        sa.Column("applies_to_all", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "availability_rule_tribute_types",
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("availability_rules.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tribute_type_id", sa.Integer(), sa.ForeignKey("tribute_types.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "appointment_slots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tribute_type_id", sa.Integer(), sa.ForeignKey("tribute_types.id", ondelete="CASCADE"), nullable=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("availability_rules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reserved_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("block_reason", sa.String(255), nullable=True),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_appointment_slots_date", "appointment_slots", ["date"])
    op.create_index("ix_appointment_slots_date_tribute", "appointment_slots", ["date", "tribute_type_id"])
    op.create_unique_constraint(
        "uq_slot_unique", "appointment_slots", ["tribute_type_id", "location_id", "date", "start_time"]
    )

    op.create_table(
        "holidays_or_blocked_days",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False, unique=True),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("is_full_day", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
    )
    op.create_index("ix_holidays_date", "holidays_or_blocked_days", ["date"], unique=True)

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reservation_code", sa.String(40), nullable=False, unique=True),
        sa.Column("tribute_type_id", sa.Integer(), sa.ForeignKey("tribute_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("slot_id", sa.Integer(), sa.ForeignKey("appointment_slots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("citizen_name", sa.String(160), nullable=False),
        sa.Column("citizen_document", sa.String(20), nullable=False),
        sa.Column("phone", sa.String(40), nullable=False),
        sa.Column("email", sa.String(120), nullable=True),
        sa.Column("reference_value", sa.String(80), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="reserved"),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_appointments_code", "appointments", ["reservation_code"], unique=True)
    op.create_index("ix_appointments_document", "appointments", ["citizen_document"])
    op.create_index("ix_appointments_status", "appointments", ["status"])

    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(80), nullable=False, unique=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("value_type", sa.String(20), nullable=False, server_default="string"),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_system_settings_key", "system_settings", ["key"], unique=True)


def downgrade():
    op.drop_index("ix_system_settings_key", table_name="system_settings")
    op.drop_table("system_settings")

    op.drop_index("ix_appointments_status", table_name="appointments")
    op.drop_index("ix_appointments_document", table_name="appointments")
    op.drop_index("ix_appointments_code", table_name="appointments")
    op.drop_table("appointments")

    op.drop_index("ix_holidays_date", table_name="holidays_or_blocked_days")
    op.drop_table("holidays_or_blocked_days")

    op.drop_constraint("uq_slot_unique", "appointment_slots", type_="unique")
    op.drop_index("ix_appointment_slots_date_tribute", table_name="appointment_slots")
    op.drop_index("ix_appointment_slots_date", table_name="appointment_slots")
    op.drop_table("appointment_slots")

    op.drop_table("availability_rule_tribute_types")
    op.drop_table("availability_rules")

    op.drop_index("ix_tribute_types_slug", table_name="tribute_types")
    op.drop_table("tribute_types")

    op.drop_table("locations")
    op.drop_table("activity_logs")
    op.drop_table("two_factor_codes")
    op.drop_table("admin_users")
