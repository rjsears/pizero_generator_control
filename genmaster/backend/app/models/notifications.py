# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/models/notifications.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Notification models for Apprise and Email channels."""

from datetime import datetime
from typing import Any, List, Optional

import sqlalchemy as sa
from sqlalchemy import Boolean, ForeignKey, Index, String, Table, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# Association table for many-to-many relationship between groups and channels
notification_group_channels = Table(
    "notification_group_channels",
    Base.metadata,
    sa.Column("group_id", sa.Integer, ForeignKey("notification_groups.id", ondelete="CASCADE"), primary_key=True),
    sa.Column("channel_id", sa.Integer, ForeignKey("notification_channels.id", ondelete="CASCADE"), primary_key=True),
)


class NotificationChannel(Base):
    """Notification channel configuration (Apprise or Email)."""

    __tablename__ = "notification_channels"
    __table_args__ = (
        Index("idx_notification_channels_slug", "slug", unique=True),
        Index("idx_notification_channels_enabled", "enabled"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Channel identification
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Channel type: 'apprise' or 'email'
    channel_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Configuration (JSON) - stores type-specific config
    # For apprise: { "url": "discord://...", "tags": ["critical"] }
    # For email: { "smtp_host": "...", "smtp_port": 587, "username": "...", "to": ["..."] }
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    groups: Mapped[List["NotificationGroup"]] = relationship(
        "NotificationGroup",
        secondary=notification_group_channels,
        back_populates="channels",
    )
    history: Mapped[List["NotificationHistory"]] = relationship(
        "NotificationHistory",
        back_populates="channel",
        cascade="all, delete-orphan",
    )

    @classmethod
    async def get_all(cls, db: AsyncSession, enabled_only: bool = False) -> List["NotificationChannel"]:
        """Get all notification channels."""
        query = select(cls)
        if enabled_only:
            query = query.where(cls.enabled == True)
        result = await db.execute(query.order_by(cls.name))
        return list(result.scalars().all())

    @classmethod
    async def get_by_id(cls, db: AsyncSession, channel_id: int) -> Optional["NotificationChannel"]:
        """Get channel by ID."""
        result = await db.execute(select(cls).where(cls.id == channel_id))
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_slug(cls, db: AsyncSession, slug: str) -> Optional["NotificationChannel"]:
        """Get channel by slug."""
        result = await db.execute(select(cls).where(cls.slug == slug))
        return result.scalar_one_or_none()


class NotificationGroup(Base):
    """Group of notification channels for bulk sending."""

    __tablename__ = "notification_groups"
    __table_args__ = (
        Index("idx_notification_groups_slug", "slug", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Group identification
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    channels: Mapped[List["NotificationChannel"]] = relationship(
        "NotificationChannel",
        secondary=notification_group_channels,
        back_populates="groups",
    )

    @classmethod
    async def get_all(cls, db: AsyncSession) -> List["NotificationGroup"]:
        """Get all notification groups."""
        result = await db.execute(select(cls).order_by(cls.name))
        return list(result.scalars().all())

    @classmethod
    async def get_by_id(cls, db: AsyncSession, group_id: int) -> Optional["NotificationGroup"]:
        """Get group by ID."""
        result = await db.execute(select(cls).where(cls.id == group_id))
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_slug(cls, db: AsyncSession, slug: str) -> Optional["NotificationGroup"]:
        """Get group by slug."""
        result = await db.execute(select(cls).where(cls.slug == slug))
        return result.scalar_one_or_none()


class NotificationHistory(Base):
    """History of sent notifications."""

    __tablename__ = "notification_history"
    __table_args__ = (
        Index("idx_notification_history_channel", "channel_id"),
        Index("idx_notification_history_event", "event_type"),
        Index("idx_notification_history_sent_at", "sent_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign key to channel
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("notification_channels.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Event information
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Delivery status
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    sent_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    channel: Mapped["NotificationChannel"] = relationship(
        "NotificationChannel",
        back_populates="history",
    )

    @classmethod
    async def get_recent(
        cls, db: AsyncSession, limit: int = 50, channel_id: Optional[int] = None
    ) -> List["NotificationHistory"]:
        """Get recent notification history."""
        query = select(cls).order_by(cls.sent_at.desc()).limit(limit)
        if channel_id:
            query = query.where(cls.channel_id == channel_id)
        result = await db.execute(query)
        return list(result.scalars().all())
