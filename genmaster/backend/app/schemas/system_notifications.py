# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/schemas/system_notifications.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 19th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""
System Notification Pydantic schemas for the comprehensive notification system.

Provides request/response schemas for:
- Event configuration (per-event settings, templates, targets)
- Global settings (maintenance, quiet hours, rate limiting, digest)
- Container monitoring configuration
- Notification history
"""

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field

# ============================================================================
# Enums
# ============================================================================


class EventSeverity(str, Enum):
    """Notification event severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class EventCategory(str, Enum):
    """Notification event categories."""

    GENMASTER = "genmaster"
    GENSLAVE = "genslave"
    GENERATOR = "generator"
    SSL = "ssl"
    CONTAINER = "container"


class EventFrequency(str, Enum):
    """Rate limiting frequency options."""

    EVERY_TIME = "every_time"
    ONCE_PER_15M = "once_per_15m"
    ONCE_PER_30M = "once_per_30m"
    ONCE_PER_HOUR = "once_per_hour"
    ONCE_PER_4H = "once_per_4h"
    ONCE_PER_12H = "once_per_12h"
    ONCE_PER_DAY = "once_per_day"


class TargetType(str, Enum):
    """Notification target types."""

    CHANNEL = "channel"
    GROUP = "group"


class NotificationStatus(str, Enum):
    """Notification delivery status."""

    SENT = "sent"
    FAILED = "failed"
    SUPPRESSED = "suppressed"
    BATCHED = "batched"


class QuietHoursAction(str, Enum):
    """Quiet hours action options."""

    REDUCE_PRIORITY = "reduce_priority"
    SUPPRESS = "suppress"


# ============================================================================
# Target Schemas
# ============================================================================


class NotificationTargetBase(BaseModel):
    """Base schema for notification targets."""

    target_type: TargetType = Field(..., description="Target type (channel or group)")
    channel_id: Optional[int] = Field(None, description="Channel ID if target_type is channel")
    group_id: Optional[int] = Field(None, description="Group ID if target_type is group")
    escalation_level: int = Field(default=1, ge=1, le=2, description="Escalation level (1=L1, 2=L2)")
    escalation_timeout_minutes: Optional[int] = Field(
        None, ge=1, le=1440, description="Override escalation timeout (minutes)"
    )


class NotificationTargetCreate(NotificationTargetBase):
    """Schema for creating a notification target."""

    pass


class NotificationTargetResponse(NotificationTargetBase):
    """Schema for notification target response."""

    id: int
    target_name: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# Event Schemas
# ============================================================================


class SystemNotificationEventBase(BaseModel):
    """Base schema for system notification events."""

    enabled: Optional[bool] = Field(None, description="Whether event notifications are enabled")
    severity: Optional[EventSeverity] = Field(None, description="Event severity level")

    # Rate limiting
    frequency: Optional[EventFrequency] = Field(None, description="Notification frequency limit")
    cooldown_minutes: Optional[int] = Field(None, ge=0, le=1440, description="Cooldown period in minutes")

    # Flapping detection
    flapping_enabled: Optional[bool] = Field(None, description="Enable flapping detection")
    flapping_threshold_count: Optional[int] = Field(None, ge=2, le=20, description="Event count threshold")
    flapping_threshold_minutes: Optional[int] = Field(None, ge=1, le=60, description="Time window in minutes")
    flapping_summary_interval: Optional[int] = Field(None, ge=5, le=120, description="Summary interval in minutes")
    notify_on_recovery: Optional[bool] = Field(None, description="Send notification when recovered from flapping")

    # Escalation
    escalation_enabled: Optional[bool] = Field(None, description="Enable L1/L2 escalation")
    escalation_timeout_minutes: Optional[int] = Field(None, ge=1, le=1440, description="L2 escalation timeout")

    # Thresholds (for resource events)
    thresholds: Optional[dict[str, Any]] = Field(None, description="Event-specific thresholds")

    # Digest
    include_in_digest: Optional[bool] = Field(None, description="Include in daily digest")

    # Custom templates
    custom_title: Optional[str] = Field(None, max_length=500, description="Custom title template")
    custom_message: Optional[str] = Field(None, description="Custom message template")


class SystemNotificationEventUpdate(SystemNotificationEventBase):
    """Schema for updating a system notification event."""

    # Target updates
    l1_targets: Optional[List[NotificationTargetCreate]] = Field(None, description="L1 (primary) targets")
    l2_targets: Optional[List[NotificationTargetCreate]] = Field(None, description="L2 (escalation) targets")


class SystemNotificationEventResponse(BaseModel):
    """Schema for system notification event response."""

    id: int
    event_type: str
    display_name: str
    description: Optional[str]
    icon: str
    category: str
    enabled: bool
    severity: str
    frequency: str
    cooldown_minutes: int
    flapping_enabled: bool
    flapping_threshold_count: int
    flapping_threshold_minutes: int
    flapping_summary_interval: int
    notify_on_recovery: bool
    escalation_enabled: bool
    escalation_timeout_minutes: int
    thresholds: Optional[dict[str, Any]]
    include_in_digest: bool
    default_title: str
    default_message: str
    custom_title: Optional[str]
    custom_message: Optional[str]
    targets: List[NotificationTargetResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SystemNotificationEventListResponse(BaseModel):
    """Schema for list of system notification events response."""

    events: List[SystemNotificationEventResponse]
    total: int
    categories: List[str]


# ============================================================================
# Global Settings Schemas
# ============================================================================


class GlobalSettingsUpdate(BaseModel):
    """Schema for updating global notification settings."""

    # Maintenance mode
    maintenance_mode: Optional[bool] = Field(None, description="Enable maintenance mode (mute all)")
    maintenance_until: Optional[datetime] = Field(None, description="Maintenance mode end time")
    maintenance_reason: Optional[str] = Field(None, max_length=500, description="Reason for maintenance")

    # Quiet hours
    quiet_hours_enabled: Optional[bool] = Field(None, description="Enable quiet hours")
    quiet_hours_start: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$", description="Quiet hours start (HH:MM)")
    quiet_hours_end: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$", description="Quiet hours end (HH:MM)")
    quiet_hours_reduce_priority: Optional[bool] = Field(
        None, description="True=reduce priority, False=suppress"
    )

    # Blackout hours
    blackout_enabled: Optional[bool] = Field(None, description="Enable blackout hours")
    blackout_start: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$", description="Blackout start (HH:MM)")
    blackout_end: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$", description="Blackout end (HH:MM)")

    # Rate limiting
    max_notifications_per_hour: Optional[int] = Field(None, ge=1, le=500, description="Max notifications per hour")
    emergency_contact_id: Optional[int] = Field(None, description="Emergency contact channel ID")

    # Daily digest
    digest_enabled: Optional[bool] = Field(None, description="Enable daily digest")
    digest_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$", description="Digest send time (HH:MM)")
    digest_severity_levels: Optional[List[str]] = Field(None, description="Severity levels to include in digest")


class GlobalSettingsResponse(BaseModel):
    """Schema for global settings response."""

    id: int
    maintenance_mode: bool
    maintenance_until: Optional[datetime]
    maintenance_reason: Optional[str]
    quiet_hours_enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str
    quiet_hours_reduce_priority: bool
    blackout_enabled: bool
    blackout_start: str
    blackout_end: str
    max_notifications_per_hour: int
    notifications_this_hour: int
    hour_started_at: Optional[datetime]
    emergency_contact_id: Optional[int]
    digest_enabled: bool
    digest_time: str
    digest_severity_levels: List[str]
    last_digest_sent: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Container Config Schemas
# ============================================================================


class ContainerConfigBase(BaseModel):
    """Base schema for container configuration."""

    enabled: bool = Field(default=True, description="Enable monitoring for this container")
    monitor_unhealthy: bool = Field(default=True, description="Monitor unhealthy state")
    monitor_restart: bool = Field(default=True, description="Monitor restarts")
    monitor_stopped: bool = Field(default=True, description="Monitor stopped state")
    monitor_high_cpu: bool = Field(default=True, description="Monitor high CPU usage")
    monitor_high_memory: bool = Field(default=True, description="Monitor high memory usage")
    cpu_threshold: int = Field(default=80, ge=1, le=100, description="CPU threshold percent")
    memory_threshold: int = Field(default=80, ge=1, le=100, description="Memory threshold percent")
    custom_targets: Optional[List[dict]] = Field(None, description="Custom notification targets")


class ContainerConfigCreate(ContainerConfigBase):
    """Schema for creating container configuration."""

    container_name: str = Field(..., min_length=1, max_length=200, description="Container name")


class ContainerConfigUpdate(ContainerConfigBase):
    """Schema for updating container configuration."""

    pass


class ContainerConfigResponse(ContainerConfigBase):
    """Schema for container configuration response."""

    id: int
    container_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContainerListResponse(BaseModel):
    """Schema for list of container configs."""

    configs: List[ContainerConfigResponse]
    total: int


class DiscoveredContainer(BaseModel):
    """Schema for a discovered container."""

    name: str
    status: str
    health: Optional[str]
    image: str
    configured: bool


class ContainerDiscoveryResponse(BaseModel):
    """Schema for container discovery response."""

    containers: List[DiscoveredContainer]
    total: int


# ============================================================================
# History Schemas
# ============================================================================


class SystemNotificationHistoryResponse(BaseModel):
    """Schema for system notification history response."""

    id: int
    event_type: str
    event_id: Optional[int]
    category: str
    target_id: Optional[str]
    target_label: Optional[str]
    severity: str
    title: str
    message: str
    event_data: Optional[dict[str, Any]]
    channels_sent: List[dict[str, Any]]
    escalation_level: int
    status: str
    suppression_reason: Optional[str]
    error_message: Optional[str]
    triggered_at: datetime
    sent_at: Optional[datetime]

    class Config:
        from_attributes = True


class HistoryListResponse(BaseModel):
    """Schema for paginated history list response."""

    items: List[SystemNotificationHistoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class HistoryStatsResponse(BaseModel):
    """Schema for history statistics."""

    total_notifications: int
    sent_count: int
    failed_count: int
    suppressed_count: int
    batched_count: int
    by_category: dict[str, int]
    by_severity: dict[str, int]


# ============================================================================
# Action Schemas
# ============================================================================


class TriggerNotificationRequest(BaseModel):
    """Schema for manually triggering a notification."""

    event_type: str = Field(..., description="Event type to trigger")
    target_id: Optional[str] = Field(None, description="Optional target identifier")
    event_data: Optional[dict[str, Any]] = Field(None, description="Event data for template variables")
    skip_rate_limiting: bool = Field(default=False, description="Skip rate limiting checks")


class TriggerNotificationResponse(BaseModel):
    """Schema for trigger notification response."""

    success: bool
    message: str
    history_id: Optional[int] = None
    suppression_reason: Optional[str] = None


class ResetTemplateRequest(BaseModel):
    """Schema for resetting event template to default."""

    reset_title: bool = Field(default=True, description="Reset title to default")
    reset_message: bool = Field(default=True, description="Reset message to default")


class BulkUpdateRequest(BaseModel):
    """Schema for bulk updating multiple events."""

    event_ids: List[int] = Field(..., min_length=1, description="Event IDs to update")
    enabled: Optional[bool] = Field(None, description="Set enabled state")
    severity: Optional[EventSeverity] = Field(None, description="Set severity")
    frequency: Optional[EventFrequency] = Field(None, description="Set frequency")
    escalation_enabled: Optional[bool] = Field(None, description="Enable/disable escalation")


class BulkUpdateResponse(BaseModel):
    """Schema for bulk update response."""

    success: bool
    updated_count: int
    message: str
