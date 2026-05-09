# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/alembic/versions/20260126_0010_010_add_auto_arm_on_connect.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 26th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Add auto-arm relay on connection restore feature.

Revision ID: 010
Revises: 009
Create Date: 2026-01-26

Adds:
- config.auto_arm_relay_on_connect: Enable auto-arm when connection is restored
- system_state.manual_disarm_active: Track when user explicitly disarms relay
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add auto_arm_relay_on_connect to config table
    op.add_column(
        "config",
        sa.Column("auto_arm_relay_on_connect", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Add manual_disarm_active to system_state table
    op.add_column(
        "system_state",
        sa.Column("manual_disarm_active", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("system_state", "manual_disarm_active")
    op.drop_column("config", "auto_arm_relay_on_connect")
