"""Add rate_limit_alert_sent column to system_notification_global_settings.

Revision ID: 022
Revises: 021
Create Date: 2026-05-14

Tracks whether the "rate limit exceeded" emergency-contact alert has
already been sent for the current hour window. Without this flag the
alert fired on every rate-limited notification, spamming the operator
with "rate limit exceeded" messages — the opposite of what a rate limit
is for. The flag is set when the alert goes out and cleared when the
hour window rolls over, so the alert is sent at most once per window.

Defaults to False so existing rows behave as "not yet alerted this
window" on upgrade.
"""

import sqlalchemy as sa

from alembic import op


# revision identifiers
revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "system_notification_global_settings",
        sa.Column(
            "rate_limit_alert_sent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("system_notification_global_settings", "rate_limit_alert_sent")
