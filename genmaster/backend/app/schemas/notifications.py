# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/schemas/notifications.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Notification-related Pydantic schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class ChannelType(str, Enum):
    """Notification channel types."""

    APPRISE = "apprise"
    EMAIL = "email"


class NotificationEvent(str, Enum):
    """Notification event types."""

    # Generator events
    GENERATOR_STARTED = "generator_started"
    GENERATOR_STOPPED = "generator_stopped"
    GENERATOR_FAILED = "generator_failed"

    # Communication events
    HEARTBEAT_LOST = "heartbeat_lost"
    HEARTBEAT_RESTORED = "heartbeat_restored"

    # Safety events
    FAILSAFE_TRIGGERED = "failsafe_triggered"

    # Schedule events
    SCHEDULE_EXECUTED = "schedule_executed"

    # System events
    SYSTEM_WARNING = "system_warning"
    SYSTEM_ERROR = "system_error"

    # Test
    TEST = "test"


# ============================================================================
# Channel Schemas
# ============================================================================


class AppriseConfig(BaseModel):
    """Apprise channel configuration."""

    url: str = Field(..., description="Apprise notification URL")
    tags: List[str] = Field(default_factory=list, description="Optional tags")


class EmailConfig(BaseModel):
    """Email channel configuration."""

    smtp_host: str = Field(..., description="SMTP server hostname")
    smtp_port: int = Field(default=587, description="SMTP server port")
    use_tls: bool = Field(default=True, description="Use TLS encryption")
    username: str = Field(..., description="SMTP username")
    password: str = Field(..., description="SMTP password (stored encrypted)")
    from_address: str = Field(..., description="From email address")
    to_addresses: List[str] = Field(..., description="Recipient email addresses")


class ChannelConfigUnion(BaseModel):
    """Union type for channel configuration."""

    # This will hold the raw config dict and be validated based on channel_type
    pass


class NotificationChannelBase(BaseModel):
    """Base schema for notification channel."""

    name: str = Field(..., min_length=1, max_length=100, description="Channel name")
    description: Optional[str] = Field(None, description="Channel description")
    channel_type: ChannelType = Field(..., description="Channel type (apprise or email)")
    config: dict[str, Any] = Field(..., description="Channel-specific configuration")
    enabled: bool = Field(default=True, description="Whether channel is enabled")

    @field_validator("name")
    @classmethod
    def generate_slug(cls, v: str) -> str:
        """Validate name is not empty."""
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v


class NotificationChannelCreate(NotificationChannelBase):
    """Schema for creating a notification channel."""

    pass


class NotificationChannelUpdate(BaseModel):
    """Schema for updating a notification channel."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    enabled: Optional[bool] = None


class NotificationChannelResponse(BaseModel):
    """Schema for notification channel response."""

    id: int
    name: str
    slug: str
    description: Optional[str]
    channel_type: str
    config: dict[str, Any]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Group Schemas
# ============================================================================


class NotificationGroupBase(BaseModel):
    """Base schema for notification group."""

    name: str = Field(..., min_length=1, max_length=100, description="Group name")
    description: Optional[str] = Field(None, description="Group description")
    enabled: bool = Field(default=True, description="Whether group is enabled")
    channel_ids: List[int] = Field(default_factory=list, description="Channel IDs in group")


class NotificationGroupCreate(NotificationGroupBase):
    """Schema for creating a notification group."""

    pass


class NotificationGroupUpdate(BaseModel):
    """Schema for updating a notification group."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    channel_ids: Optional[List[int]] = None


class NotificationGroupResponse(BaseModel):
    """Schema for notification group response."""

    id: int
    name: str
    slug: str
    description: Optional[str]
    enabled: bool
    channels: List[NotificationChannelResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# History Schemas
# ============================================================================


class NotificationHistoryResponse(BaseModel):
    """Schema for notification history response."""

    id: int
    channel_id: int
    channel_name: Optional[str] = None
    event_type: str
    title: str
    message: str
    success: bool
    error_message: Optional[str]
    sent_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Send Notification Schemas
# ============================================================================


class SendNotificationRequest(BaseModel):
    """Schema for sending a notification."""

    event_type: NotificationEvent = Field(..., description="Event type")
    title: str = Field(..., min_length=1, max_length=200, description="Notification title")
    message: str = Field(..., min_length=1, description="Notification message")
    channel_ids: Optional[List[int]] = Field(None, description="Specific channels to send to")
    group_ids: Optional[List[int]] = Field(None, description="Groups to send to")


class SendNotificationResponse(BaseModel):
    """Schema for send notification response."""

    success: bool
    total_sent: int
    total_failed: int
    results: List[dict[str, Any]]


class TestChannelRequest(BaseModel):
    """Schema for testing a channel."""

    title: str = Field(default="Test Notification", description="Test notification title")
    message: str = Field(default="This is a test notification from GenMaster.", description="Test message")


class TestChannelResponse(BaseModel):
    """Schema for test channel response."""

    success: bool
    message: str
    error: Optional[str] = None
