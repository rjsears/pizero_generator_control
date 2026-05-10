"""Add boot arming policy and boot-disarmed notification event.

Revision ID: 013
Revises: 012
Create Date: 2026-05-09

Adds:
- config.boot_arming_policy: 'fail_safe' (default) or 'preserve_state'
  Controls whether the slave_relay_armed flag is reset to False on
  GenMaster boot. Default 'fail_safe' is the safer behavior — operator
  must explicitly re-arm after any GenMaster restart.
- system_notification_events row for 'boot_disarmed_failsafe' so users
  can configure a notification when the fail-safe boot policy disarms
  the relay.
"""

import time

import sqlalchemy as sa
from alembic import op


# revision identifiers
revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add boot_arming_policy column to config
    op.add_column(
        "config",
        sa.Column(
            "boot_arming_policy",
            sa.String(length=32),
            nullable=False,
            server_default="fail_safe",
        ),
    )

    # Seed the new notification event so users can configure who gets pinged
    # when the fail-safe boot policy disarms the relay.
    now = int(time.time())
    op.execute(
        sa.text(
            """
            INSERT INTO system_notification_events (
                event_type, display_name, description, icon, category,
                severity, enabled, default_title, default_message,
                created_at, updated_at
            ) VALUES (
                'boot_disarmed_failsafe',
                'Relay Disarmed on Boot (Fail-Safe)',
                'The fail-safe boot policy automatically disarmed the relay after a GenMaster restart',
                'ShieldExclamationIcon',
                'generator',
                'warning',
                true,
                'Generator Disarmed After Reboot — Action Required',
                'GenMaster restarted with the fail-safe boot policy enabled.\n\nThe generator relay has been automatically DISARMED for safety.\n\nThe generator WILL NOT START automatically until you log in and re-arm it from the web interface.',
                :now, :now
            )
            ON CONFLICT (event_type) DO NOTHING
            """
        ),
        {"now": now},
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM system_notification_events WHERE event_type = 'boot_disarmed_failsafe'")
    )
    op.drop_column("config", "boot_arming_policy")
