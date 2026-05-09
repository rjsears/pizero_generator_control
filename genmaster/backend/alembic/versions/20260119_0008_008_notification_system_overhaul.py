"""Notification system overhaul - add system notification tables

Revision ID: 008
Revises: 007
Create Date: 2026-01-19

Adds tables for:
- system_notification_events: Per-event configuration
- system_notification_targets: L1/L2 escalation targets
- system_notification_global_settings: Global settings singleton
- system_notification_state: Runtime state tracking
- system_notification_container_configs: Per-container monitoring config
- system_notification_history: Comprehensive notification history
"""

import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


# Default system notification events to seed
DEFAULT_EVENTS = [
    {
        "event_type": "generator_started",
        "display_name": "Generator Started",
        "description": "Generator has been started",
        "icon": "PlayIcon",
        "category": "generator",
        "severity": "info",
        "enabled": True,
        "default_title": "Generator Started",
        "default_message": "Generator Started at {start_time}\nReason: {reason}",
    },
    {
        "event_type": "generator_stopped",
        "display_name": "Generator Stopped",
        "description": "Generator has been stopped",
        "icon": "StopIcon",
        "category": "generator",
        "severity": "info",
        "enabled": True,
        "default_title": "Generator Stopped",
        "default_message": "Generator Stopped ({reason})\nTotal Run Time: {runtime}\nTotal Fuel Consumed: {fuel_gallons} gal/{fuel_type}",
    },
    {
        "event_type": "generator_relay_enabled",
        "display_name": "Generator Relay Enabled",
        "description": "Generator relay has been armed for automatic operations",
        "icon": "BoltIcon",
        "category": "generator",
        "severity": "info",
        "enabled": True,
        "default_title": "Generator Relay Enabled",
        "default_message": "The generator relay has been enabled. Automatic generator operations are now available.",
    },
    {
        "event_type": "generator_relay_disabled",
        "display_name": "Generator Relay Disabled",
        "description": "Generator relay has been disarmed - automatic operations disabled",
        "icon": "BoltSlashIcon",
        "category": "generator",
        "severity": "warning",
        "enabled": True,
        "default_title": "Generator Relay Disabled",
        "default_message": "The generator relay has been disabled.\n\nWARNING: You MUST log in and re-enable the generator relay to enable automatic operation.",
    },
    {
        "event_type": "generator_max_runtime_manual_reset",
        "display_name": "Max Runtime - Manual Reset Required",
        "description": "Generator exceeded maximum runtime and requires manual reset",
        "icon": "ExclamationTriangleIcon",
        "category": "generator",
        "severity": "critical",
        "enabled": True,
        "default_title": "GENERATOR MAX RUNTIME EXCEEDED",
        "default_message": "Generator exceeded maximum run time of {max_minutes} minutes.\n\nGenerator was automatically shut down and requires a manual reset.\n\nYou must log in and re-enable the generator relay to enable automatic generator operations.",
    },
    {
        "event_type": "generator_max_runtime_cooldown",
        "display_name": "Max Runtime - Cooldown Active",
        "description": "Generator exceeded maximum runtime, cooldown period active",
        "icon": "ClockIcon",
        "category": "generator",
        "severity": "warning",
        "enabled": True,
        "default_title": "Generator Max Runtime - Cooldown Active",
        "default_message": "Generator exceeded maximum run time of {max_minutes} minutes.\n\nGenerator was automatically shut down but no further action is required on your part.\n\nYour generator will be re-enabled automatically in {cooldown_period}.",
    },
    {
        "event_type": "generator_failsafe_triggered",
        "display_name": "Failsafe Triggered",
        "description": "GenSlave failsafe triggered - relay turned off due to communication loss",
        "icon": "ShieldExclamationIcon",
        "category": "generator",
        "severity": "critical",
        "enabled": True,
        "default_title": "FAILSAFE TRIGGERED",
        "default_message": "GenSlave failsafe triggered at {time}.\n\nThe generator relay has been turned OFF due to loss of communication with GenMaster.\n\nYou must restore communication and re-enable the generator relay.",
    },
    {
        "event_type": "genslave_comm_lost",
        "display_name": "GenSlave Communication Lost",
        "description": "Lost communication with GenSlave controller",
        "icon": "SignalSlashIcon",
        "category": "genslave",
        "severity": "critical",
        "enabled": True,
        "default_title": "COMMUNICATION LOST WITH GENSLAVE",
        "default_message": "Lost communication with GenSlave at {time}.\n\nAutomatic generator operations are not available.",
    },
    {
        "event_type": "genslave_comm_restored",
        "display_name": "GenSlave Communication Restored",
        "description": "Communication with GenSlave has been restored",
        "icon": "SignalIcon",
        "category": "genslave",
        "severity": "info",
        "enabled": True,
        "default_title": "GenSlave Communication Restored",
        "default_message": "GenSlave back online.\n\nAutomatic generator operations are {relay_status}.\n{relay_warning}",
    },
    {
        "event_type": "genmaster_disk_space_low",
        "display_name": "GenMaster Disk Space Low",
        "description": "GenMaster host disk space is running low",
        "icon": "CircleStackIcon",
        "category": "genmaster",
        "severity": "warning",
        "enabled": True,
        "default_title": "GenMaster Disk Space Low",
        "default_message": "Disk space low on GenMaster: {path} at {percent}% usage",
    },
    {
        "event_type": "genmaster_high_cpu",
        "display_name": "GenMaster High CPU Usage",
        "description": "GenMaster host CPU usage is high",
        "icon": "CpuChipIcon",
        "category": "genmaster",
        "severity": "warning",
        "enabled": True,
        "default_title": "GenMaster High CPU Usage",
        "default_message": "High CPU usage on GenMaster: {percent}% for {duration}",
    },
    {
        "event_type": "genmaster_high_memory",
        "display_name": "GenMaster High Memory Usage",
        "description": "GenMaster host memory usage is high",
        "icon": "ServerIcon",
        "category": "genmaster",
        "severity": "warning",
        "enabled": True,
        "default_title": "GenMaster High Memory Usage",
        "default_message": "High memory usage on GenMaster: {percent}% ({used}/{total})",
    },
    {
        "event_type": "genmaster_high_temperature",
        "display_name": "GenMaster High CPU Temperature",
        "description": "GenMaster host CPU temperature is high",
        "icon": "FireIcon",
        "category": "genmaster",
        "severity": "warning",
        "enabled": True,
        "default_title": "GenMaster High CPU Temperature",
        "default_message": "High CPU temperature on GenMaster: {temp}°C",
    },
    {
        "event_type": "genslave_disk_space_low",
        "display_name": "GenSlave Disk Space Low",
        "description": "GenSlave host disk space is running low",
        "icon": "CircleStackIcon",
        "category": "genslave",
        "severity": "warning",
        "enabled": True,
        "default_title": "GenSlave Disk Space Low",
        "default_message": "Disk space low on GenSlave: {path} at {percent}% usage",
    },
    {
        "event_type": "genslave_high_cpu",
        "display_name": "GenSlave High CPU Usage",
        "description": "GenSlave host CPU usage is high",
        "icon": "CpuChipIcon",
        "category": "genslave",
        "severity": "warning",
        "enabled": True,
        "default_title": "GenSlave High CPU Usage",
        "default_message": "High CPU usage on GenSlave: {percent}% for {duration}",
    },
    {
        "event_type": "genslave_high_memory",
        "display_name": "GenSlave High Memory Usage",
        "description": "GenSlave host memory usage is high",
        "icon": "ServerIcon",
        "category": "genslave",
        "severity": "warning",
        "enabled": True,
        "default_title": "GenSlave High Memory Usage",
        "default_message": "High memory usage on GenSlave: {percent}% ({used}/{total})",
    },
    {
        "event_type": "genslave_high_temperature",
        "display_name": "GenSlave High CPU Temperature",
        "description": "GenSlave host CPU temperature is high",
        "icon": "FireIcon",
        "category": "genslave",
        "severity": "warning",
        "enabled": True,
        "default_title": "GenSlave High CPU Temperature",
        "default_message": "High CPU temperature on GenSlave: {temp}°C",
    },
    {
        "event_type": "certificate_expiring",
        "display_name": "SSL Certificate Expiring",
        "description": "SSL certificate is expiring soon",
        "icon": "ShieldExclamationIcon",
        "category": "ssl",
        "severity": "warning",
        "enabled": True,
        "default_title": "SSL Certificate Expiring",
        "default_message": "SSL certificate expiring in {days} days for {domain}",
    },
    {
        "event_type": "certificate_expired",
        "display_name": "SSL Certificate Expired",
        "description": "SSL certificate has expired",
        "icon": "ShieldExclamationIcon",
        "category": "ssl",
        "severity": "critical",
        "enabled": True,
        "default_title": "SSL Certificate EXPIRED",
        "default_message": "SSL certificate has EXPIRED for {domain}",
    },
    {
        "event_type": "certificate_renewed",
        "display_name": "SSL Certificate Renewed",
        "description": "SSL certificate has been successfully renewed",
        "icon": "ShieldCheckIcon",
        "category": "ssl",
        "severity": "info",
        "enabled": True,
        "include_in_digest": True,
        "default_title": "SSL Certificate Renewed",
        "default_message": "SSL certificate successfully renewed for {domain}",
    },
    {
        "event_type": "container_unhealthy",
        "display_name": "Container Unhealthy",
        "description": "Docker container health check failed",
        "icon": "ExclamationCircleIcon",
        "category": "container",
        "severity": "warning",
        "enabled": True,
        "default_title": "Container Unhealthy",
        "default_message": "Container '{container_name}' is unhealthy",
    },
    {
        "event_type": "container_stopped",
        "display_name": "Container Stopped",
        "description": "Docker container has stopped unexpectedly",
        "icon": "StopCircleIcon",
        "category": "container",
        "severity": "warning",
        "enabled": True,
        "default_title": "Container Stopped",
        "default_message": "Container '{container_name}' has stopped",
    },
    {
        "event_type": "container_restarted",
        "display_name": "Container Restarted",
        "description": "Docker container has restarted",
        "icon": "ArrowPathIcon",
        "category": "container",
        "severity": "info",
        "enabled": True,
        "include_in_digest": True,
        "default_title": "Container Restarted",
        "default_message": "Container '{container_name}' has restarted",
    },
    {
        "event_type": "container_high_cpu",
        "display_name": "Container High CPU",
        "description": "Docker container is using high CPU",
        "icon": "CpuChipIcon",
        "category": "container",
        "severity": "warning",
        "enabled": True,
        "default_title": "Container High CPU",
        "default_message": "Container '{container_name}' high CPU: {percent}%",
    },
    {
        "event_type": "container_high_memory",
        "display_name": "Container High Memory",
        "description": "Docker container is using high memory",
        "icon": "ServerIcon",
        "category": "container",
        "severity": "warning",
        "enabled": True,
        "default_title": "Container High Memory",
        "default_message": "Container '{container_name}' high memory: {percent}%",
    },
]


def upgrade() -> None:
    # Create system_notification_events table
    op.create_table(
        "system_notification_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(50), nullable=False, server_default="BellIcon"),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("severity", sa.String(20), nullable=False, server_default="warning"),
        sa.Column("frequency", sa.String(50), nullable=False, server_default="every_time"),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("flapping_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("flapping_threshold_count", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("flapping_threshold_minutes", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("flapping_summary_interval", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("notify_on_recovery", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("escalation_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("escalation_timeout_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("thresholds", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("include_in_digest", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("default_title", sa.String(500), nullable=False, server_default=""),
        sa.Column("default_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("custom_title", sa.String(500), nullable=True),
        sa.Column("custom_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_type", name="uq_sne_event_type"),
    )
    op.create_index("idx_sne_event_type", "system_notification_events", ["event_type"], unique=True)
    op.create_index("idx_sne_category", "system_notification_events", ["category"])
    op.create_index("idx_sne_enabled", "system_notification_events", ["enabled"])

    # Create system_notification_targets table
    op.create_table(
        "system_notification_targets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=True),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column("escalation_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("escalation_timeout_minutes", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["system_notification_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["channel_id"], ["notification_channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["notification_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id", "target_type", "escalation_level", "channel_id", "group_id",
            name="uq_snt_event_target_level"
        ),
    )
    op.create_index("idx_snt_event_id", "system_notification_targets", ["event_id"])
    op.create_index("idx_snt_channel_id", "system_notification_targets", ["channel_id"])
    op.create_index("idx_snt_group_id", "system_notification_targets", ["group_id"])

    # Create system_notification_global_settings table
    op.create_table(
        "system_notification_global_settings",
        sa.Column("id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("maintenance_mode", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("maintenance_until", sa.DateTime(), nullable=True),
        sa.Column("maintenance_reason", sa.String(500), nullable=True),
        sa.Column("quiet_hours_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("quiet_hours_start", sa.String(5), nullable=False, server_default="22:00"),
        sa.Column("quiet_hours_end", sa.String(5), nullable=False, server_default="07:00"),
        sa.Column("quiet_hours_reduce_priority", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("blackout_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("blackout_start", sa.String(5), nullable=False, server_default="23:00"),
        sa.Column("blackout_end", sa.String(5), nullable=False, server_default="06:00"),
        sa.Column("max_notifications_per_hour", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("notifications_this_hour", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hour_started_at", sa.DateTime(), nullable=True),
        sa.Column("emergency_contact_id", sa.Integer(), nullable=True),
        sa.Column("digest_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("digest_time", sa.String(5), nullable=False, server_default="08:00"),
        sa.Column("digest_severity_levels", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='["info"]'),
        sa.Column("last_digest_sent", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["emergency_contact_id"], ["notification_channels.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create system_notification_state table
    op.create_table(
        "system_notification_state",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("target_id", sa.String(200), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(), nullable=True),
        sa.Column("event_count_in_window", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_start", sa.DateTime(), nullable=True),
        sa.Column("is_flapping", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("flapping_started_at", sa.DateTime(), nullable=True),
        sa.Column("last_summary_at", sa.DateTime(), nullable=True),
        sa.Column("escalation_triggered_at", sa.DateTime(), nullable=True),
        sa.Column("escalation_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_type", "target_id", name="uq_sns_event_target"),
    )
    op.create_index("idx_sns_event_type", "system_notification_state", ["event_type"])
    op.create_index("idx_sns_target_id", "system_notification_state", ["target_id"])

    # Create system_notification_container_configs table
    op.create_table(
        "system_notification_container_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("container_name", sa.String(200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("monitor_unhealthy", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("monitor_restart", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("monitor_stopped", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("monitor_high_cpu", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("monitor_high_memory", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("cpu_threshold", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("memory_threshold", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("custom_targets", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("container_name", name="uq_sncc_container_name"),
    )
    op.create_index("idx_sncc_container_name", "system_notification_container_configs", ["container_name"], unique=True)

    # Create system_notification_history table
    op.create_table(
        "system_notification_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("target_id", sa.String(200), nullable=True),
        sa.Column("target_label", sa.String(200), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("event_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("channels_sent", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("escalation_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("suppression_reason", sa.String(200), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("triggered_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["system_notification_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_snh_event_type", "system_notification_history", ["event_type"])
    op.create_index("idx_snh_triggered_at", "system_notification_history", ["triggered_at"])
    op.create_index("idx_snh_status", "system_notification_history", ["status"])
    op.create_index("idx_snh_category", "system_notification_history", ["category"])

    # Seed default notification events
    conn = op.get_bind()
    for event in DEFAULT_EVENTS:
        thresholds = event.get("thresholds")
        include_in_digest = event.get("include_in_digest", False)
        conn.execute(
            sa.text("""
                INSERT INTO system_notification_events
                (event_type, display_name, description, icon, category, severity, enabled,
                 default_title, default_message, thresholds, include_in_digest)
                VALUES (:event_type, :display_name, :description, :icon, :category, :severity, :enabled,
                        :default_title, :default_message, :thresholds, :include_in_digest)
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
                "thresholds": json.dumps(thresholds) if thresholds else None,
                "include_in_digest": include_in_digest,
            }
        )

    # Insert the global settings singleton row
    conn.execute(
        sa.text("INSERT INTO system_notification_global_settings (id) VALUES (1)")
    )


def downgrade() -> None:
    # Drop tables in reverse order (respect foreign keys)
    op.drop_index("idx_snh_category", table_name="system_notification_history")
    op.drop_index("idx_snh_status", table_name="system_notification_history")
    op.drop_index("idx_snh_triggered_at", table_name="system_notification_history")
    op.drop_index("idx_snh_event_type", table_name="system_notification_history")
    op.drop_table("system_notification_history")

    op.drop_index("idx_sncc_container_name", table_name="system_notification_container_configs")
    op.drop_table("system_notification_container_configs")

    op.drop_index("idx_sns_target_id", table_name="system_notification_state")
    op.drop_index("idx_sns_event_type", table_name="system_notification_state")
    op.drop_table("system_notification_state")

    op.drop_table("system_notification_global_settings")

    op.drop_index("idx_snt_group_id", table_name="system_notification_targets")
    op.drop_index("idx_snt_channel_id", table_name="system_notification_targets")
    op.drop_index("idx_snt_event_id", table_name="system_notification_targets")
    op.drop_table("system_notification_targets")

    op.drop_index("idx_sne_enabled", table_name="system_notification_events")
    op.drop_index("idx_sne_category", table_name="system_notification_events")
    op.drop_index("idx_sne_event_type", table_name="system_notification_events")
    op.drop_table("system_notification_events")
