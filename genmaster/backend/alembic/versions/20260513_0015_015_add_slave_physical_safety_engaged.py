"""Add slave_physical_safety_engaged column to system_state.

Revision ID: 015
Revises: 014
Create Date: 2026-05-13

Tracks whether the GenSlave hardware E-stop (EPO) is currently engaged.
Populated from the GenSlave heartbeat reply (and corresponding fast-poll
endpoints) on every cycle. Nullable so existing rows survive the upgrade
without needing a backfill — GenMaster's heartbeat-status update will
write the first real value within ~60s of restart.

Pattern mirrors the existing slave_relay_state / slave_relay_armed
columns: GenSlave is the source of truth, GenMaster caches the most
recent reported value for state-machine decisions and UI display.
"""

import sqlalchemy as sa

from alembic import op


# revision identifiers
revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "system_state",
        sa.Column(
            "slave_physical_safety_engaged",
            sa.Boolean(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("system_state", "slave_physical_safety_engaged")
