# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/models/system_notifications.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 19th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""
System Notification models for event-driven notifications with L1/L2 escalation,
rate limiting, quiet hours, and per-event configuration.

This module provides the database models for the comprehensive notification system
that mirrors the n8n_nginx implementation.
"""

from datetime import datetime
from typing import Any, List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.notifications import NotificationChannel, NotificationGroup


# Default system notification events to seed the database
DEFAULT_SYSTEM_NOTIFICATION_EVENTS = [
    # Generator Events
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
    # Communication Events
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
    # Host Events - GenMaster
    {
        "event_type": "genmaster_disk_space_low",
        "display_name": "GenMaster Disk Space Low",
        "description": "GenMaster host disk space is running low",
        "icon": "CircleStackIcon",
        "category": "genmaster",
        "severity": "warning",
        "enabled": True,
        "thresholds": {"percent": 90},
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
        "thresholds": {"percent": 80, "duration_minutes": 5},
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
        "thresholds": {"percent": 85},
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
        "thresholds": {"celsius": 80},
        "default_title": "GenMaster High CPU Temperature",
        "default_message": "High CPU temperature on GenMaster: {temp}°C",
    },
    # Host Events - GenSlave (monitored and sent by GenMaster)
    {
        "event_type": "genslave_disk_space_low",
        "display_name": "GenSlave Disk Space Low",
        "description": "GenSlave host disk space is running low",
        "icon": "CircleStackIcon",
        "category": "genslave",
        "severity": "warning",
        "enabled": True,
        "thresholds": {"percent": 90},
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
        "thresholds": {"percent": 80, "duration_minutes": 5},
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
        "thresholds": {"percent": 85},
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
        "thresholds": {"celsius": 70},  # Pi Zero runs hotter
        "default_title": "GenSlave High CPU Temperature",
        "default_message": "High CPU temperature on GenSlave: {temp}°C",
    },
    # SSL Events
    {
        "event_type": "certificate_expiring",
        "display_name": "SSL Certificate Expiring",
        "description": "SSL certificate is expiring soon",
        "icon": "ShieldExclamationIcon",
        "category": "ssl",
        "severity": "warning",
        "enabled": True,
        "thresholds": {"days": 14},
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
    # Container Events
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
        "thresholds": {"percent": 80},
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
        "thresholds": {"percent": 80},
        "default_title": "Container High Memory",
        "default_message": "Container '{container_name}' high memory: {percent}%",
    },
]


class SystemNotificationEvent(Base):
    """
    Configuration for each system notification event type.

    Stores per-event settings including enabled state, severity,
    rate limiting, flapping detection, escalation, and message templates.
    """

    __tablename__ = "system_notification_events"
    __table_args__ = (
        Index("idx_sne_event_type", "event_type", unique=True),
        Index("idx_sne_category", "category"),
        Index("idx_sne_enabled", "enabled"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Event identification
    event_type: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(String(50), default="BellIcon")
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # genmaster, genslave, generator, ssl, container

    # Status and severity
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    severity: Mapped[str] = mapped_column(String(20), default="warning")  # info, warning, critical

    # Rate limiting
    frequency: Mapped[str] = mapped_column(String(50), default="every_time")
    # Options: every_time, once_per_15m, once_per_30m, once_per_hour, once_per_4h, once_per_12h, once_per_day
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=0)

    # Flapping detection
    flapping_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    flapping_threshold_count: Mapped[int] = mapped_column(Integer, default=3)
    flapping_threshold_minutes: Mapped[int] = mapped_column(Integer, default=10)
    flapping_summary_interval: Mapped[int] = mapped_column(Integer, default=15)
    notify_on_recovery: Mapped[bool] = mapped_column(Boolean, default=True)

    # Escalation (L1/L2)
    escalation_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_timeout_minutes: Mapped[int] = mapped_column(Integer, default=30)

    # Thresholds (for resource events like disk space, CPU, etc.)
    thresholds: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Daily digest
    include_in_digest: Mapped[bool] = mapped_column(Boolean, default=False)

    # Custom message templates (user-editable)
    default_title: Mapped[str] = mapped_column(String(500), default="")
    default_message: Mapped[str] = mapped_column(Text, default="")
    custom_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    custom_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    targets: Mapped[List["SystemNotificationTarget"]] = relationship(
        "SystemNotificationTarget",
        back_populates="event",
        cascade="all, delete-orphan",
    )

    @property
    def title_template(self) -> str:
        """Get the effective title template (custom or default)."""
        return self.custom_title or self.default_title

    @property
    def message_template(self) -> str:
        """Get the effective message template (custom or default)."""
        return self.custom_message or self.default_message

    @classmethod
    async def get_all(
        cls,
        db: AsyncSession,
        category: Optional[str] = None,
        enabled_only: bool = False,
    ) -> List["SystemNotificationEvent"]:
        """Get all system notification events."""
        query = select(cls)
        if category:
            query = query.where(cls.category == category)
        if enabled_only:
            query = query.where(cls.enabled == True)
        result = await db.execute(query.order_by(cls.category, cls.display_name))
        return list(result.scalars().all())

    @classmethod
    async def get_by_event_type(
        cls, db: AsyncSession, event_type: str
    ) -> Optional["SystemNotificationEvent"]:
        """Get event by event_type."""
        result = await db.execute(select(cls).where(cls.event_type == event_type))
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_id(
        cls, db: AsyncSession, event_id: int
    ) -> Optional["SystemNotificationEvent"]:
        """Get event by ID."""
        result = await db.execute(select(cls).where(cls.id == event_id))
        return result.scalar_one_or_none()


class SystemNotificationTarget(Base):
    """
    Links events to notification channels or groups with L1/L2 escalation levels.

    L1 (escalation_level=1): Primary targets, notified immediately
    L2 (escalation_level=2): Escalation targets, notified after timeout or if L1 fails
    """

    __tablename__ = "system_notification_targets"
    __table_args__ = (
        UniqueConstraint(
            "event_id", "target_type", "escalation_level", "channel_id", "group_id",
            name="uq_snt_event_target_level"
        ),
        Index("idx_snt_event_id", "event_id"),
        Index("idx_snt_channel_id", "channel_id"),
        Index("idx_snt_group_id", "group_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign key to event
    event_id: Mapped[int] = mapped_column(
        ForeignKey("system_notification_events.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Target type and reference
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "channel" or "group"
    channel_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("notification_channels.id", ondelete="CASCADE"),
        nullable=True,
    )
    group_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("notification_groups.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Escalation level
    escalation_level: Mapped[int] = mapped_column(Integer, default=1)  # 1 = L1 (primary), 2 = L2 (escalation)

    # Per-target escalation timeout override (null = use event default)
    escalation_timeout_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    event: Mapped["SystemNotificationEvent"] = relationship(
        "SystemNotificationEvent",
        back_populates="targets",
    )
    channel: Mapped[Optional["NotificationChannel"]] = relationship(
        "NotificationChannel",
        foreign_keys=[channel_id],
    )
    group: Mapped[Optional["NotificationGroup"]] = relationship(
        "NotificationGroup",
        foreign_keys=[group_id],
    )

    @property
    def target_name(self) -> str:
        """Get the target name for display."""
        if self.target_type == "channel" and self.channel:
            return self.channel.name
        elif self.target_type == "group" and self.group:
            return self.group.name
        return "Unknown"


class SystemNotificationGlobalSettings(Base):
    """
    Singleton table for global notification settings.

    Contains maintenance mode, quiet hours, blackout hours,
    rate limiting, and daily digest configuration.
    """

    __tablename__ = "system_notification_global_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)

    # Maintenance Mode - mutes all notifications
    maintenance_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    maintenance_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    maintenance_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Quiet Hours - reduce priority or suppress during specified hours
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    quiet_hours_start: Mapped[str] = mapped_column(String(5), default="22:00")  # HH:MM
    quiet_hours_end: Mapped[str] = mapped_column(String(5), default="07:00")
    quiet_hours_reduce_priority: Mapped[bool] = mapped_column(Boolean, default=True)  # True = reduce, False = suppress

    # Blackout Hours - full mute during specified hours
    blackout_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    blackout_start: Mapped[str] = mapped_column(String(5), default="23:00")
    blackout_end: Mapped[str] = mapped_column(String(5), default="06:00")

    # Rate Limiting
    max_notifications_per_hour: Mapped[int] = mapped_column(Integer, default=50)
    notifications_this_hour: Mapped[int] = mapped_column(Integer, default=0)
    hour_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Emergency Contact - notified if rate limit exceeded
    emergency_contact_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("notification_channels.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Daily Digest
    digest_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    digest_time: Mapped[str] = mapped_column(String(5), default="08:00")  # HH:MM
    digest_severity_levels: Mapped[list] = mapped_column(JSONB, default=["info"])
    last_digest_sent: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    emergency_contact: Mapped[Optional["NotificationChannel"]] = relationship(
        "NotificationChannel",
        foreign_keys=[emergency_contact_id],
    )

    @classmethod
    async def get_instance(cls, db: AsyncSession) -> "SystemNotificationGlobalSettings":
        """Get or create the singleton settings instance."""
        result = await db.execute(select(cls).where(cls.id == 1))
        instance = result.scalar_one_or_none()
        if not instance:
            instance = cls(id=1)
            db.add(instance)
            await db.commit()
            await db.refresh(instance)
        return instance


class SystemNotificationState(Base):
    """
    Runtime state tracking for rate limiting and flapping detection.

    Tracks per-event, per-target state including last notification time,
    flapping window event counts, and escalation status.
    """

    __tablename__ = "system_notification_state"
    __table_args__ = (
        UniqueConstraint("event_type", "target_id", name="uq_sns_event_target"),
        Index("idx_sns_event_type", "event_type"),
        Index("idx_sns_target_id", "target_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Event and target identification
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(200), nullable=False)  # Container name or identifier

    # Cooldown tracking
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Flapping detection
    event_count_in_window: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_flapping: Mapped[bool] = mapped_column(Boolean, default=False)
    flapping_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_summary_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Escalation tracking
    escalation_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    escalation_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    @classmethod
    async def get_state(
        cls, db: AsyncSession, event_type: str, target_id: str
    ) -> Optional["SystemNotificationState"]:
        """Get state for a specific event/target combination."""
        result = await db.execute(
            select(cls).where(
                cls.event_type == event_type,
                cls.target_id == target_id,
            )
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_or_create(
        cls, db: AsyncSession, event_type: str, target_id: str
    ) -> "SystemNotificationState":
        """Get or create state for a specific event/target combination."""
        state = await cls.get_state(db, event_type, target_id)
        if not state:
            state = cls(event_type=event_type, target_id=target_id)
            db.add(state)
            await db.flush()
        return state


class SystemNotificationContainerConfig(Base):
    """
    Per-container monitoring configuration.

    Allows overriding default monitoring settings for specific containers,
    including which events to monitor and custom thresholds.
    """

    __tablename__ = "system_notification_container_configs"
    __table_args__ = (
        Index("idx_sncc_container_name", "container_name", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Container identification
    container_name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)

    # Master enable/disable for this container
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Granular monitoring flags
    monitor_unhealthy: Mapped[bool] = mapped_column(Boolean, default=True)
    monitor_restart: Mapped[bool] = mapped_column(Boolean, default=True)
    monitor_stopped: Mapped[bool] = mapped_column(Boolean, default=True)
    monitor_high_cpu: Mapped[bool] = mapped_column(Boolean, default=True)
    monitor_high_memory: Mapped[bool] = mapped_column(Boolean, default=True)

    # Custom thresholds (override event defaults)
    cpu_threshold: Mapped[int] = mapped_column(Integer, default=80)
    memory_threshold: Mapped[int] = mapped_column(Integer, default=80)

    # Custom targets (override event targets) - JSON array of {type, id}
    custom_targets: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    @classmethod
    async def get_by_name(
        cls, db: AsyncSession, container_name: str
    ) -> Optional["SystemNotificationContainerConfig"]:
        """Get container config by name."""
        result = await db.execute(
            select(cls).where(cls.container_name == container_name)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_all(cls, db: AsyncSession) -> List["SystemNotificationContainerConfig"]:
        """Get all container configs."""
        result = await db.execute(select(cls).order_by(cls.container_name))
        return list(result.scalars().all())


class SystemNotificationHistory(Base):
    """
    Comprehensive history of system notifications.

    Records all notification attempts including successful sends,
    failures, suppressions (due to rate limiting, quiet hours, etc.),
    and batched notifications for digest.
    """

    __tablename__ = "system_notification_history"
    __table_args__ = (
        Index("idx_snh_event_type", "event_type"),
        Index("idx_snh_triggered_at", "triggered_at"),
        Index("idx_snh_status", "status"),
        Index("idx_snh_category", "category"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Event information
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("system_notification_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)

    # Target identification (e.g., container name)
    target_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    target_label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # Human-readable

    # Notification content
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    event_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Delivery information
    channels_sent: Mapped[list] = mapped_column(JSONB, default=[])  # [{type, id, name, level}]
    escalation_level: Mapped[int] = mapped_column(Integer, default=1)

    # Status tracking
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # sent, failed, suppressed, batched
    suppression_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    triggered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship
    event: Mapped[Optional["SystemNotificationEvent"]] = relationship(
        "SystemNotificationEvent",
        foreign_keys=[event_id],
    )

    @classmethod
    async def get_recent(
        cls,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        event_type: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List["SystemNotificationHistory"]:
        """Get recent notification history with optional filters."""
        query = select(cls)
        if event_type:
            query = query.where(cls.event_type == event_type)
        if category:
            query = query.where(cls.category == category)
        if status:
            query = query.where(cls.status == status)
        query = query.order_by(cls.triggered_at.desc()).offset(offset).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @classmethod
    async def count(
        cls,
        db: AsyncSession,
        event_type: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """Count notification history records with optional filters."""
        from sqlalchemy import func as sa_func
        query = select(sa_func.count(cls.id))
        if event_type:
            query = query.where(cls.event_type == event_type)
        if category:
            query = query.where(cls.category == category)
        if status:
            query = query.where(cls.status == status)
        result = await db.execute(query)
        return result.scalar() or 0

    @classmethod
    async def cleanup_old_records(cls, db: AsyncSession, days: int = 60) -> int:
        """Delete notification history records older than specified days."""
        from datetime import timedelta
        from sqlalchemy import delete
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await db.execute(
            delete(cls).where(cls.triggered_at < cutoff)
        )
        await db.commit()
        return result.rowcount
