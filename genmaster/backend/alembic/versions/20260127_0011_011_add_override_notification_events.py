"""Add override notification events.

Revision ID: 011
Revises: 010
Create Date: 2026-01-27

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add override_enabled and override_disabled notification events."""
    conn = op.get_bind()

    # Define the new override events
    events = [
        {
            "event_type": "override_enabled",
            "display_name": "Override Enabled",
            "description": "Manual override has been enabled (Victron signal ignored)",
            "icon": "ShieldExclamationIcon",
            "category": "generator",
            "severity": "warning",
            "enabled": True,
            "default_title": "Manual Override Enabled",
            "default_message": "Manual override enabled: {type}. Victron signal will be ignored.",
        },
        {
            "event_type": "override_disabled",
            "display_name": "Override Disabled",
            "description": "Manual override has been disabled (returning to automatic control)",
            "icon": "ShieldCheckIcon",
            "category": "generator",
            "severity": "info",
            "enabled": True,
            "default_title": "Manual Override Disabled",
            "default_message": "Manual override disabled. Returning to automatic Victron control.",
        },
    ]

    for event in events:
        conn.execute(
            sa.text("""
                INSERT INTO system_notification_events
                (event_type, display_name, description, icon, category, severity, enabled,
                 default_title, default_message, include_in_digest)
                VALUES (:event_type, :display_name, :description, :icon, :category, :severity, :enabled,
                        :default_title, :default_message, :include_in_digest)
                ON CONFLICT (event_type) DO NOTHING
            """),
            {
                "event_type": event["event_type"],
                "display_name": event["display_name"],
                "description": event["description"],
                "icon": event["icon"],
                "category": event["category"],
                "severity": event["severity"],
                "enabled": event["enabled"],
                "default_title": event["default_title"],
                "default_message": event["default_message"],
                "include_in_digest": False,
            }
        )


def downgrade() -> None:
    """Remove override notification events."""
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM system_notification_events WHERE event_type IN ('override_enabled', 'override_disabled')")
    )
