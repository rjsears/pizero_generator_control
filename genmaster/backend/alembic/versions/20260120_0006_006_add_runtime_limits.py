"""Add runtime limits configuration and lockout/cooldown state

Revision ID: 006
Revises: 005
Create Date: 2026-01-20

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add runtime limits columns to config table
    op.add_column(
        "config",
        sa.Column("runtime_limits_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "config",
        sa.Column("min_run_minutes", sa.Integer(), nullable=False, server_default="5"),
    )
    op.add_column(
        "config",
        sa.Column("max_run_minutes", sa.Integer(), nullable=False, server_default="480"),
    )
    op.add_column(
        "config",
        sa.Column("max_runtime_action", sa.String(), nullable=False, server_default="manual_reset"),
    )
    op.add_column(
        "config",
        sa.Column("cooldown_duration_minutes", sa.Integer(), nullable=False, server_default="60"),
    )

    # Add lockout/cooldown columns to system_state table
    op.add_column(
        "system_state",
        sa.Column("runtime_lockout_active", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "system_state",
        sa.Column("runtime_lockout_started", sa.Integer(), nullable=True),
    )
    op.add_column(
        "system_state",
        sa.Column("runtime_lockout_reason", sa.String(), nullable=True),
    )
    op.add_column(
        "system_state",
        sa.Column("cooldown_active", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "system_state",
        sa.Column("cooldown_end_time", sa.Integer(), nullable=True),
    )

    # Update generator_runs stop_reason constraint to include 'max_runtime'
    op.drop_constraint("chk_stop_reason", "generator_runs", type_="check")
    op.create_check_constraint(
        "chk_stop_reason",
        "generator_runs",
        "stop_reason IS NULL OR stop_reason IN "
        "('victron', 'manual', 'scheduled_end', 'exercise_end', 'comm_loss', 'override', 'error', 'max_runtime')",
    )


def downgrade() -> None:
    # Revert generator_runs stop_reason constraint
    op.drop_constraint("chk_stop_reason", "generator_runs", type_="check")
    op.create_check_constraint(
        "chk_stop_reason",
        "generator_runs",
        "stop_reason IS NULL OR stop_reason IN "
        "('victron', 'manual', 'scheduled_end', 'exercise_end', 'comm_loss', 'override', 'error')",
    )

    # Remove lockout/cooldown columns from system_state
    op.drop_column("system_state", "cooldown_end_time")
    op.drop_column("system_state", "cooldown_active")
    op.drop_column("system_state", "runtime_lockout_reason")
    op.drop_column("system_state", "runtime_lockout_started")
    op.drop_column("system_state", "runtime_lockout_active")

    # Remove runtime limits columns from config
    op.drop_column("config", "cooldown_duration_minutes")
    op.drop_column("config", "max_runtime_action")
    op.drop_column("config", "max_run_minutes")
    op.drop_column("config", "min_run_minutes")
    op.drop_column("config", "runtime_limits_enabled")
