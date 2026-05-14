"""Add manual-run-reminder config + boot-state notification event.

Revision ID: 021
Revises: 020
Create Date: 2026-05-14

Phase 5b — two additions:

  1. `config.manual_run_reminder_enabled` (bool, default true) and
     `config.manual_run_reminder_interval_hours` (int, default 2).
     Drive the background reminder timer that nudges the operator while
     a manual / HOA-Run generator run is active.

  2. The `genmaster_boot_hardware_state` notification event. Fired once
     at GenMaster startup when the EPO is engaged or the HOA selector is
     not in Auto — tells the operator what hardware-switch state the
     system came up in. (Nothing fires on a fully-normal boot.)

INSERT for the event uses ON CONFLICT DO NOTHING so re-runs are safe.
"""

import sqlalchemy as sa

from alembic import op


# revision identifiers
revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "config",
        sa.Column(
            "manual_run_reminder_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )
    op.add_column(
        "config",
        sa.Column(
            "manual_run_reminder_interval_hours",
            sa.Integer(),
            nullable=False,
            server_default="2",
        ),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO system_notification_events
            (event_type, display_name, description, icon, category,
             severity, enabled, default_title, default_message,
             include_in_digest)
            VALUES (:event_type, :display_name, :description, :icon,
                    :category, :severity, :enabled, :default_title,
                    :default_message, :include_in_digest)
            ON CONFLICT (event_type) DO NOTHING
            """
        ),
        {
            "event_type": "genmaster_boot_hardware_state",
            "display_name": "GenMaster Boot — Hardware Switch State",
            "description": (
                "Fired once at GenMaster startup when the EPO is engaged "
                "or the HOA selector is not in Auto"
            ),
            "icon": "InformationCircleIcon",
            "category": "genmaster",
            "severity": "warning",
            "enabled": True,
            "default_title": "GenMaster Online — Hardware Switch State",
            "default_message": "{state_message}",
            "include_in_digest": False,
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM system_notification_events "
            "WHERE event_type = 'genmaster_boot_hardware_state'"
        )
    )
    op.drop_column("config", "manual_run_reminder_interval_hours")
    op.drop_column("config", "manual_run_reminder_enabled")
