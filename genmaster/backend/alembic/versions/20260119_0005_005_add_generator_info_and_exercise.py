"""Add generator_info and exercise_schedule tables, fuel tracking to generator_runs

Revision ID: 005
Revises: 004
Create Date: 2026-01-19

"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create generator_info table
    op.create_table(
        "generator_info",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("manufacturer", sa.String(), nullable=True),
        sa.Column("model_number", sa.String(), nullable=True),
        sa.Column("serial_number", sa.String(), nullable=True),
        sa.Column("fuel_type", sa.String(), nullable=True),
        sa.Column("load_expected", sa.Integer(), nullable=True),
        sa.Column("fuel_consumption_50", sa.Float(), nullable=True),
        sa.Column("fuel_consumption_100", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("id = 1", name="chk_generator_info_single_row"),
        sa.CheckConstraint(
            "fuel_type IS NULL OR fuel_type IN ('lpg', 'natural_gas', 'diesel')",
            name="chk_fuel_type",
        ),
        sa.CheckConstraint(
            "load_expected IS NULL OR load_expected IN (50, 100)",
            name="chk_load_expected",
        ),
    )

    # Insert initial row with id=1
    op.execute(
        "INSERT INTO generator_info (id, updated_at) VALUES (1, NOW())"
    )

    # Create exercise_schedule table
    op.create_table(
        "exercise_schedule",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("frequency_days", sa.Integer(), nullable=False, default=7),
        sa.Column("start_time", sa.String(), nullable=False, default="10:00"),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, default=15),
        sa.Column("last_exercise_date", sa.Date(), nullable=True),
        sa.Column("next_exercise_date", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("id = 1", name="chk_exercise_schedule_single_row"),
        sa.CheckConstraint(
            "frequency_days >= 1 AND frequency_days <= 365",
            name="chk_frequency_days_range",
        ),
        sa.CheckConstraint(
            "duration_minutes >= 1 AND duration_minutes <= 480",
            name="chk_duration_minutes_range",
        ),
    )

    # Insert initial row with id=1 and defaults
    op.execute(
        "INSERT INTO exercise_schedule (id, enabled, frequency_days, start_time, duration_minutes, updated_at) "
        "VALUES (1, false, 7, '10:00', 15, NOW())"
    )

    # Add fuel tracking columns to generator_runs
    op.add_column(
        "generator_runs",
        sa.Column("fuel_type_at_run", sa.String(), nullable=True),
    )
    op.add_column(
        "generator_runs",
        sa.Column("load_at_run", sa.Integer(), nullable=True),
    )
    op.add_column(
        "generator_runs",
        sa.Column("fuel_consumption_rate", sa.Float(), nullable=True),
    )
    op.add_column(
        "generator_runs",
        sa.Column("estimated_fuel_used", sa.Float(), nullable=True),
    )

    # Update system_state run_trigger constraint to include 'exercise'
    # First, drop the existing constraint
    op.drop_constraint("chk_run_trigger", "system_state", type_="check")
    # Then, add the new constraint with 'exercise' included
    op.create_check_constraint(
        "chk_run_trigger",
        "system_state",
        "run_trigger IN ('idle', 'victron', 'manual', 'scheduled', 'exercise')",
    )


def downgrade() -> None:
    # Revert system_state run_trigger constraint
    op.drop_constraint("chk_run_trigger", "system_state", type_="check")
    op.create_check_constraint(
        "chk_run_trigger",
        "system_state",
        "run_trigger IN ('idle', 'victron', 'manual', 'scheduled')",
    )

    # Remove fuel tracking columns from generator_runs
    op.drop_column("generator_runs", "estimated_fuel_used")
    op.drop_column("generator_runs", "fuel_consumption_rate")
    op.drop_column("generator_runs", "load_at_run")
    op.drop_column("generator_runs", "fuel_type_at_run")

    # Drop exercise_schedule table
    op.drop_table("exercise_schedule")

    # Drop generator_info table
    op.drop_table("generator_info")
