"""Remove the obsolete dynamic system settings table.

Revision ID: b7c1d4e8f902
Revises: 8f4d2a9e3c12
"""
from alembic import op


revision = "b7c1d4e8f902"
down_revision = "8f4d2a9e3c12"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("ix_system_settings_key", table_name="system_settings")
    op.drop_table("system_settings")


def downgrade():
    raise NotImplementedError("system_settings was replaced by static application configuration")
