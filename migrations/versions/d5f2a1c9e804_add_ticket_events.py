"""Add the ticket_events audit table.

Revision ID: d5f2a1c9e804
Revises: c4e8f1a9b703
"""

from alembic import op
import sqlalchemy as sa


revision = "d5f2a1c9e804"
down_revision = "c4e8f1a9b703"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ticket_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_status", sa.String(20), nullable=True),
        sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ticket_events_appointment_id", "ticket_events", ["appointment_id"])


def downgrade():
    op.drop_index("ix_ticket_events_appointment_id", table_name="ticket_events")
    op.drop_table("ticket_events")
