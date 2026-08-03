"""Add the login second-factor lookup index.

Revision ID: c4e8f1a9b703
Revises: b7c1d4e8f902
"""

from alembic import op


revision = "c4e8f1a9b703"
down_revision = "b7c1d4e8f902"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_two_factor_codes_login_lookup",
        "two_factor_codes",
        ["user_id", "purpose", "consumed_at", "created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_two_factor_codes_login_lookup", table_name="two_factor_codes")
