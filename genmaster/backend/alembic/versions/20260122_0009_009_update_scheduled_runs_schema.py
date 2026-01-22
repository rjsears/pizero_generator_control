# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/alembic/versions/20260122_0009_009_update_scheduled_runs_schema.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 22nd, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Update scheduled_runs to use start_time and days_of_week format.

Revision ID: 009
Revises: 008
Create Date: 2026-01-22

This migration updates the scheduled_runs table from one-time scheduling
(scheduled_start timestamp) to weekly scheduling (start_time + days_of_week).
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns
    op.add_column(
        "scheduled_runs",
        sa.Column("start_time", sa.String(length=5), nullable=True),
    )
    op.add_column(
        "scheduled_runs",
        sa.Column("days_of_week", sa.String(length=50), nullable=True),
    )

    # Set default values for new columns
    op.execute("UPDATE scheduled_runs SET start_time = '09:00' WHERE start_time IS NULL")
    op.execute("UPDATE scheduled_runs SET days_of_week = '[]' WHERE days_of_week IS NULL")

    # Make columns non-nullable after setting defaults
    op.alter_column("scheduled_runs", "start_time", nullable=False)
    op.alter_column("scheduled_runs", "days_of_week", nullable=False)

    # Drop old columns (no longer used)
    op.drop_column("scheduled_runs", "scheduled_start")
    op.drop_column("scheduled_runs", "recurring")
    op.drop_column("scheduled_runs", "recurrence_pattern")
    op.drop_column("scheduled_runs", "recurrence_end_date")


def downgrade() -> None:
    # Add back old columns
    op.add_column(
        "scheduled_runs",
        sa.Column("scheduled_start", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "scheduled_runs",
        sa.Column("recurring", sa.Boolean(), nullable=True, server_default="false"),
    )
    op.add_column(
        "scheduled_runs",
        sa.Column("recurrence_pattern", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "scheduled_runs",
        sa.Column("recurrence_end_date", sa.BigInteger(), nullable=True),
    )

    # Set defaults for old columns
    op.execute("UPDATE scheduled_runs SET scheduled_start = 0 WHERE scheduled_start IS NULL")
    op.alter_column("scheduled_runs", "scheduled_start", nullable=False)
    op.alter_column("scheduled_runs", "recurring", nullable=False)

    # Drop new columns
    op.drop_column("scheduled_runs", "start_time")
    op.drop_column("scheduled_runs", "days_of_week")
