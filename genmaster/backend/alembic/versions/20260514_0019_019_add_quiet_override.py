"""Add Quiet override columns to system_state.

Revision ID: 019
Revises: 018
Create Date: 2026-05-14

Phase 4c — operator-initiated temporary override of the HOA Quiet
selector position. While the override window is active, automation
triggers (Victron / scheduled / exercise) fire normally even though
the HOA selector is physically in Quiet.

Two columns on system_state:

  * `quiet_override_active`     — bool, whether an override is in effect
  * `quiet_override_expires_at` — unix timestamp the override window ends

Per failsafe.md decision #2 the duration is operator-selected every
time (no default, no "continuous" option). When the window expires the
state machine lazily clears the flag and Quiet re-engages.

Note: this is revision 019, not 016. Migration 017's docstring reserved
the "016" slot for this work, but 017 + 018 shipped and deployed before
4c was built, so the chain is already past that point. Alembic does not
require contiguous revision numbers — down_revision below makes the
chain explicit.
"""

import sqlalchemy as sa

from alembic import op


# revision identifiers
revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "system_state",
        sa.Column(
            "quiet_override_active",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "system_state",
        sa.Column(
            "quiet_override_expires_at",
            sa.Integer(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("system_state", "quiet_override_expires_at")
    op.drop_column("system_state", "quiet_override_active")
