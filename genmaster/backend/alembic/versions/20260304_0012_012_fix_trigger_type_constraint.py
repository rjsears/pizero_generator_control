"""Fix generator_runs constraints to include exercise trigger type

Revision ID: 012
Revises: 011
Create Date: 2026-03-04

The initial migration forgot to update chk_trigger_type and chk_stop_reason
constraints when exercise runs were added in migration 005.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old constraints
    op.drop_constraint("chk_trigger_type", "generator_runs", type_="check")
    op.drop_constraint("chk_stop_reason", "generator_runs", type_="check")

    # Create new constraints with exercise and max_runtime included
    op.create_check_constraint(
        "chk_trigger_type",
        "generator_runs",
        "trigger_type IN ('victron', 'manual', 'scheduled', 'exercise')",
    )
    op.create_check_constraint(
        "chk_stop_reason",
        "generator_runs",
        "stop_reason IS NULL OR stop_reason IN "
        "('victron', 'manual', 'scheduled_end', 'exercise_end', 'comm_loss', 'override', 'error', 'max_runtime')",
    )


def downgrade() -> None:
    # Revert to old constraints (will fail if exercise data exists)
    op.drop_constraint("chk_trigger_type", "generator_runs", type_="check")
    op.drop_constraint("chk_stop_reason", "generator_runs", type_="check")

    op.create_check_constraint(
        "chk_trigger_type",
        "generator_runs",
        "trigger_type IN ('victron', 'manual', 'scheduled')",
    )
    op.create_check_constraint(
        "chk_stop_reason",
        "generator_runs",
        "stop_reason IS NULL OR stop_reason IN "
        "('victron', 'manual', 'scheduled_end', 'comm_loss', 'override', 'error')",
    )
