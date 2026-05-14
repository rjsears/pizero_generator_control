"""Add EPO + HOA notification events.

Revision ID: 020
Revises: 019
Create Date: 2026-05-14

Phase 5 — seeds the ten operator-facing notification events for the
EPO / HOA hardware-switch feature into system_notification_events.
Mirrors the DEFAULT_SYSTEM_NOTIFICATION_EVENTS list in
app/models/system_notifications.py (kept in sync so fresh installs and
upgraded installs end up with the same set).

Nine of the ten are wired to event-driven triggers in this same phase.
The tenth, `manual_run_reminder`, is defined here so the operator can
configure its routing now, but only starts firing once the Phase 5b
background reminder timer lands. Defining it ahead of the timer means
no follow-up migration is needed.

Uses ON CONFLICT DO NOTHING so re-running against a DB that already has
some of these rows is harmless.
"""

import sqlalchemy as sa

from alembic import op


# revision identifiers
revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


_EVENTS = [
    {
        "event_type": "hardware_safety_engaged_genslave",
        "display_name": "Hardware Safety (EPO) Engaged",
        "description": "The hardware E-stop at the generator has been pressed",
        "icon": "ExclamationTriangleIcon",
        "category": "genslave",
        "severity": "warning",
        "default_title": "GenSlave EPO Engaged",
        "default_message": (
            "The hardware safety interlock (E-stop) at the generator has "
            "been engaged. The generator cannot run from any source until "
            "the E-stop is physically released."
        ),
    },
    {
        "event_type": "hardware_safety_released_genslave",
        "display_name": "Hardware Safety (EPO) Released",
        "description": "The hardware E-stop at the generator has been released",
        "icon": "ShieldCheckIcon",
        "category": "genslave",
        "severity": "info",
        "default_title": "GenSlave EPO Released",
        "default_message": (
            "The hardware safety interlock at the generator has been "
            "released. Automation resumes on the next heartbeat if a run "
            "is still being requested."
        ),
    },
    {
        "event_type": "quiet_mode_engaged_genmaster",
        "display_name": "Quiet Mode Engaged",
        "description": "The HOA selector was turned to the Quiet position",
        "icon": "InformationCircleIcon",
        "category": "generator",
        "severity": "info",
        "default_title": "Quiet Mode Engaged",
        "default_message": (
            "The HOA selector at GenMaster has been turned to Quiet. "
            "Automatic generator runs are suppressed. Manual runs and the "
            "web-based Quiet override are still available."
        ),
    },
    {
        "event_type": "quiet_mode_released_genmaster",
        "display_name": "Quiet Mode Released",
        "description": "The HOA selector was turned out of the Quiet position",
        "icon": "InformationCircleIcon",
        "category": "generator",
        "severity": "info",
        "default_title": "Quiet Mode Released",
        "default_message": (
            "The HOA selector has been turned out of Quiet. Automatic "
            "generator operations have resumed."
        ),
    },
    {
        "event_type": "manual_run_started_genmaster_switch",
        "display_name": "Manual Run Started (HOA Switch)",
        "description": "A manual run was started by turning the HOA selector to Run",
        "icon": "PlayIcon",
        "category": "generator",
        "severity": "info",
        "default_title": "Manual Run Started — HOA Switch",
        "default_message": (
            "A manual generator run was started by turning the HOA "
            "selector to Run. The generator will run until the selector "
            "is returned to Auto or Quiet."
        ),
    },
    {
        "event_type": "manual_run_ended_genmaster_switch",
        "display_name": "Manual Run Ended (HOA Switch)",
        "description": "An HOA-switch manual run ended when the selector left Run",
        "icon": "StopIcon",
        "category": "generator",
        "severity": "info",
        "default_title": "Manual Run Ended — HOA Switch",
        "default_message": (
            "The HOA selector was turned out of Run. The manual generator "
            "run has ended."
        ),
    },
    {
        "event_type": "manual_run_blocked_by_safety",
        "display_name": "Run Blocked by Safety Interlock",
        "description": "A generator start was blocked because the EPO is engaged",
        "icon": "ExclamationTriangleIcon",
        "category": "generator",
        "severity": "warning",
        "default_title": "Generator Start Blocked — EPO Engaged",
        "default_message": (
            "A generator start was requested ({trigger}), but the GenSlave "
            "hardware safety interlock (EPO) is engaged. The generator "
            "cannot start. Release the E-stop at the generator to proceed."
        ),
    },
    {
        "event_type": "auto_run_suppressed_by_quiet",
        "display_name": "Auto Run Suppressed by Quiet Mode",
        "description": "An automation trigger was suppressed because Quiet Mode is active",
        "icon": "InformationCircleIcon",
        "category": "generator",
        "severity": "warning",
        "default_title": "Automatic Run Suppressed — Quiet Mode",
        "default_message": (
            "An automatic generator run was requested ({trigger}), but "
            "Quiet Mode is active. The run was suppressed. If you need "
            "power, use a manual start or the Quiet override in the web UI."
        ),
    },
    {
        "event_type": "quiet_override_enabled",
        "display_name": "Quiet Override Enabled",
        "description": "A temporary override of Quiet Mode was enabled by the operator",
        "icon": "InformationCircleIcon",
        "category": "generator",
        "severity": "info",
        "default_title": "Quiet Override Enabled",
        "default_message": (
            "A temporary Quiet override was enabled for {duration_minutes} "
            "minutes. Automatic generator runs will fire normally until "
            "the override expires, then Quiet re-engages."
        ),
    },
    {
        "event_type": "manual_run_reminder",
        "display_name": "Manual Run Reminder",
        "description": "Periodic reminder that a manual generator run is still active",
        "icon": "ClockIcon",
        "category": "generator",
        "severity": "info",
        "default_title": "Manual Run Still Active",
        "default_message": (
            "A manual generator run has been active for {hours} hours. If "
            "this is unintended, stop the generator or return the HOA "
            "selector to Auto."
        ),
    },
]


def upgrade() -> None:
    conn = op.get_bind()
    for event in _EVENTS:
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
                "event_type": event["event_type"],
                "display_name": event["display_name"],
                "description": event["description"],
                "icon": event["icon"],
                "category": event["category"],
                "severity": event["severity"],
                "enabled": True,
                "default_title": event["default_title"],
                "default_message": event["default_message"],
                "include_in_digest": False,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    event_types = tuple(e["event_type"] for e in _EVENTS)
    conn.execute(
        sa.text(
            "DELETE FROM system_notification_events "
            "WHERE event_type IN :types"
        ).bindparams(sa.bindparam("types", expanding=True)),
        {"types": list(event_types)},
    )
