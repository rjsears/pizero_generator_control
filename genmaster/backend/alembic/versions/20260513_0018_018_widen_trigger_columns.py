"""Widen trigger and stop_reason columns to fit local_switch_genmaster.

Revision ID: 018
Revises: 017
Create Date: 2026-05-13

Migration 017 added `local_switch_genmaster` and `local_switch_genmaster_end`
to the CHECK constraints, but the underlying columns are still
``VARCHAR(20)`` from the original 0001 schema. The new values are 22 and
26 characters respectively, so any INSERT or UPDATE with them fails with
``StringDataRightTruncationError``.

This migration widens the three affected columns to ``VARCHAR(40)``:

  * `system_state.run_trigger`
  * `generator_runs.trigger_type`
  * `generator_runs.stop_reason`

40 chars is generous — comfortably fits the longest current value
(`local_switch_genmaster_end` = 26) plus headroom for future trigger
sources without another column-widening migration.

The downgrade attempts to revert to ``VARCHAR(20)``, which will FAIL if
any existing row has a value longer than 20 characters. Treat downgrade
as a destructive operation only safe immediately after a clean upgrade.
"""

import sqlalchemy as sa

from alembic import op


# revision identifiers
revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "system_state",
        "run_trigger",
        type_=sa.String(length=40),
        existing_type=sa.String(length=20),
        existing_nullable=False,
        existing_server_default="idle",
    )
    op.alter_column(
        "generator_runs",
        "trigger_type",
        type_=sa.String(length=40),
        existing_type=sa.String(length=20),
        existing_nullable=False,
    )
    op.alter_column(
        "generator_runs",
        "stop_reason",
        type_=sa.String(length=40),
        existing_type=sa.String(length=20),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Will fail if any row already holds a value longer than 20 chars
    # (e.g. an existing local_switch_genmaster run). Operator must
    # truncate or delete those rows first.
    op.alter_column(
        "system_state",
        "run_trigger",
        type_=sa.String(length=20),
        existing_type=sa.String(length=40),
        existing_nullable=False,
        existing_server_default="idle",
    )
    op.alter_column(
        "generator_runs",
        "trigger_type",
        type_=sa.String(length=20),
        existing_type=sa.String(length=40),
        existing_nullable=False,
    )
    op.alter_column(
        "generator_runs",
        "stop_reason",
        type_=sa.String(length=20),
        existing_type=sa.String(length=40),
        existing_nullable=True,
    )
