"""Add fuel tracking reset timestamp to config

Revision ID: 007
Revises: 006
Create Date: 2026-01-19

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add fuel tracking reset timestamp to config table
    op.add_column(
        "config",
        sa.Column("fuel_tracking_reset_timestamp", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    # Remove fuel tracking reset timestamp from config
    op.drop_column("config", "fuel_tracking_reset_timestamp")
