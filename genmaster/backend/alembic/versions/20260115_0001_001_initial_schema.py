# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/alembic/versions/20260115_0001_001_initial_schema.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Initial schema - create all tables for GenMaster.

Revision ID: 001
Revises:
Create Date: 2026-01-15
"""

from typing import Sequence, Union

import bcrypt as bcrypt_lib
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create update_updated_at_column function for triggers
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """
    )

    # =========================================================================
    # Table: scheduled_runs (must be created before generator_runs due to FK)
    # =========================================================================
    op.create_table(
        "scheduled_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("scheduled_start", sa.BigInteger(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("recurring", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("recurrence_pattern", sa.String(length=100), nullable=True),
        sa.Column("recurrence_end_date", sa.BigInteger(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_executed", sa.BigInteger(), nullable=True),
        sa.Column("next_execution", sa.BigInteger(), nullable=True),
        sa.Column("execution_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_scheduled_runs_next_execution", "scheduled_runs", ["next_execution"]
    )
    op.create_index("idx_scheduled_runs_enabled", "scheduled_runs", ["enabled"])

    op.execute(
        """
        CREATE TRIGGER update_scheduled_runs_updated_at
            BEFORE UPDATE ON scheduled_runs
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # =========================================================================
    # Table: generator_runs
    # =========================================================================
    op.create_table(
        "generator_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("start_time", sa.BigInteger(), nullable=False),
        sa.Column("stop_time", sa.BigInteger(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("stop_reason", sa.String(length=20), nullable=True),
        sa.Column("scheduled_run_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["scheduled_run_id"],
            ["scheduled_runs.id"],
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "trigger_type IN ('victron', 'manual', 'scheduled')",
            name="chk_trigger_type",
        ),
        sa.CheckConstraint(
            "stop_reason IS NULL OR stop_reason IN "
            "('victron', 'manual', 'scheduled_end', 'comm_loss', 'override', 'error')",
            name="chk_stop_reason",
        ),
    )
    op.create_index("idx_generator_runs_start_time", "generator_runs", ["start_time"])
    op.create_index(
        "idx_generator_runs_trigger_type", "generator_runs", ["trigger_type"]
    )
    op.create_index("idx_generator_runs_created_at", "generator_runs", ["created_at"])

    # =========================================================================
    # Table: system_state (singleton)
    # =========================================================================
    op.create_table(
        "system_state",
        sa.Column("id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "generator_running", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "automation_armed", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("automation_armed_at", sa.BigInteger(), nullable=True),
        sa.Column("automation_armed_by", sa.String(length=50), nullable=True),
        sa.Column("generator_start_time", sa.BigInteger(), nullable=True),
        sa.Column("current_run_id", sa.Integer(), nullable=True),
        sa.Column(
            "run_trigger", sa.String(length=20), nullable=False, server_default="idle"
        ),
        sa.Column(
            "override_enabled", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "override_type", sa.String(length=20), nullable=False, server_default="none"
        ),
        sa.Column(
            "victron_signal_state", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("victron_last_change", sa.BigInteger(), nullable=True),
        sa.Column("last_heartbeat_sent", sa.BigInteger(), nullable=True),
        sa.Column("last_heartbeat_received", sa.BigInteger(), nullable=True),
        sa.Column(
            "missed_heartbeat_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "slave_connection_status",
            sa.String(length=20),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("slave_relay_state", sa.Boolean(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["current_run_id"],
            ["generator_runs.id"],
        ),
        sa.CheckConstraint("id = 1", name="chk_single_row"),
        sa.CheckConstraint(
            "run_trigger IN ('idle', 'victron', 'manual', 'scheduled')",
            name="chk_run_trigger",
        ),
        sa.CheckConstraint(
            "override_type IN ('none', 'force_run', 'force_stop')",
            name="chk_override_type",
        ),
        sa.CheckConstraint(
            "slave_connection_status IN ('connected', 'disconnected', 'unknown')",
            name="chk_connection_status",
        ),
    )

    op.execute(
        """
        CREATE TRIGGER update_system_state_updated_at
            BEFORE UPDATE ON system_state
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # =========================================================================
    # Table: config (singleton)
    # =========================================================================
    op.create_table(
        "config",
        sa.Column("id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "heartbeat_interval_seconds",
            sa.Integer(),
            nullable=False,
            server_default="60",
        ),
        sa.Column(
            "heartbeat_failure_threshold",
            sa.Integer(),
            nullable=False,
            server_default="3",
        ),
        sa.Column(
            "slave_api_url",
            sa.String(length=255),
            nullable=False,
            server_default="http://genslave:8000",
        ),
        sa.Column(
            "slave_api_secret",
            sa.String(length=255),
            nullable=False,
            server_default="change-me",
        ),
        sa.Column("webhook_base_url", sa.String(length=255), nullable=True),
        sa.Column("webhook_secret", sa.String(length=255), nullable=True),
        sa.Column("webhook_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("temp_warning_celsius", sa.Integer(), nullable=False, server_default="70"),
        sa.Column("temp_critical_celsius", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("disk_warning_percent", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("disk_critical_percent", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("ram_warning_percent", sa.Integer(), nullable=False, server_default="85"),
        sa.Column("tailscale_hostname", sa.String(length=50), nullable=True),
        sa.Column("tailscale_ip", sa.String(length=45), nullable=True),
        sa.Column(
            "cloudflare_enabled", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("cloudflare_hostname", sa.String(length=255), nullable=True),
        sa.Column("ssl_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ssl_domain", sa.String(length=255), nullable=True),
        sa.Column("ssl_email", sa.String(length=255), nullable=True),
        sa.Column("ssl_dns_provider", sa.String(length=50), nullable=True),
        sa.Column(
            "event_log_retention_days", sa.Integer(), nullable=False, server_default="30"
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="chk_config_single_row"),
    )

    op.execute(
        """
        CREATE TRIGGER update_config_updated_at
            BEFORE UPDATE ON config
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # =========================================================================
    # Table: event_log
    # =========================================================================
    op.create_table(
        "event_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("event_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "severity", sa.String(length=20), nullable=False, server_default="INFO"
        ),
        sa.Column(
            "source", sa.String(length=50), nullable=False, server_default="genmaster"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "severity IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')",
            name="chk_severity",
        ),
    )
    op.create_index("idx_event_log_created_at", "event_log", ["created_at"])
    op.create_index("idx_event_log_event_type", "event_log", ["event_type"])
    op.create_index("idx_event_log_severity", "event_log", ["severity"])
    # GIN index for JSONB queries
    op.execute(
        "CREATE INDEX idx_event_log_data ON event_log USING GIN (event_data);"
    )

    # =========================================================================
    # Table: users
    # =========================================================================
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("idx_users_username", "users", ["username"], unique=True)

    op.execute(
        """
        CREATE TRIGGER update_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # =========================================================================
    # Table: sessions
    # =========================================================================
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("token"),
    )
    op.create_index("idx_sessions_token", "sessions", ["token"], unique=True)
    op.create_index("idx_sessions_user_id", "sessions", ["user_id"])
    op.create_index("idx_sessions_expires_at", "sessions", ["expires_at"])

    # =========================================================================
    # Table: settings
    # =========================================================================
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index("idx_settings_key", "settings", ["key"], unique=True)

    op.execute(
        """
        CREATE TRIGGER update_settings_updated_at
            BEFORE UPDATE ON settings
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # =========================================================================
    # Insert default data
    # =========================================================================

    # Insert default system_state row (singleton)
    op.execute("INSERT INTO system_state (id) VALUES (1);")

    # Insert default config row (singleton)
    op.execute("INSERT INTO config (id) VALUES (1);")

    # Insert default admin user (password: admin - CHANGE IN PRODUCTION!)
    admin_password_hash = bcrypt_lib.hashpw("admin".encode(), bcrypt_lib.gensalt()).decode()
    op.execute(
        f"""
        INSERT INTO users (username, password_hash, is_active, is_admin)
        VALUES ('admin', '{admin_password_hash}', true, true);
        """
    )

    # Insert initial event log entry
    op.execute(
        """
        INSERT INTO event_log (event_type, event_data, severity, source)
        VALUES ('SYSTEM_INITIALIZED', '{"version": "1.0.0"}', 'INFO', 'migration');
        """
    )


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table("settings")
    op.drop_table("sessions")
    op.drop_table("users")
    op.drop_table("event_log")
    op.drop_table("config")
    op.drop_table("system_state")
    op.drop_table("generator_runs")
    op.drop_table("scheduled_runs")

    # Drop the trigger function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
