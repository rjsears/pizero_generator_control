# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/alembic/versions/20260117_0002_002_add_notifications.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 17th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Add notification tables for Apprise and Email.

Revision ID: 002
Revises: 001
Create Date: 2026-01-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Table: notification_channels
    # =========================================================================
    op.create_table(
        "notification_channels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("channel_type", sa.String(length=20), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
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
        sa.UniqueConstraint("slug"),
        sa.CheckConstraint(
            "channel_type IN ('apprise', 'email')",
            name="chk_channel_type",
        ),
    )
    op.create_index("idx_notification_channels_slug", "notification_channels", ["slug"], unique=True)
    op.create_index("idx_notification_channels_enabled", "notification_channels", ["enabled"])

    op.execute(
        """
        CREATE TRIGGER update_notification_channels_updated_at
            BEFORE UPDATE ON notification_channels
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # =========================================================================
    # Table: notification_groups
    # =========================================================================
    op.create_table(
        "notification_groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
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
        sa.UniqueConstraint("slug"),
    )
    op.create_index("idx_notification_groups_slug", "notification_groups", ["slug"], unique=True)

    op.execute(
        """
        CREATE TRIGGER update_notification_groups_updated_at
            BEFORE UPDATE ON notification_groups
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # =========================================================================
    # Table: notification_group_channels (many-to-many association)
    # =========================================================================
    op.create_table(
        "notification_group_channels",
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("group_id", "channel_id"),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["notification_groups.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["notification_channels.id"],
            ondelete="CASCADE",
        ),
    )

    # =========================================================================
    # Table: notification_history
    # =========================================================================
    op.create_table(
        "notification_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["notification_channels.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("idx_notification_history_channel", "notification_history", ["channel_id"])
    op.create_index("idx_notification_history_event", "notification_history", ["event_type"])
    op.create_index("idx_notification_history_sent_at", "notification_history", ["sent_at"])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("notification_history")
    op.drop_table("notification_group_channels")
    op.drop_table("notification_groups")
    op.drop_table("notification_channels")
