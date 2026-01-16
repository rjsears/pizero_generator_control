# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/schemas/webhook.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Webhook-related Pydantic schemas."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class WebhookEvent(str, Enum):
    """Webhook event types."""

    # Generator events
    GENERATOR_STARTED_VICTRON = "generator.started.victron"
    GENERATOR_STARTED_MANUAL = "generator.started.manual"
    GENERATOR_STARTED_SCHEDULED = "generator.started.scheduled"
    GENERATOR_STOPPED_VICTRON = "generator.stopped.victron"
    GENERATOR_STOPPED_MANUAL = "generator.stopped.manual"
    GENERATOR_STOPPED_SCHEDULED_END = "generator.stopped.scheduled_end"
    GENERATOR_STOPPED_COMM_LOSS = "generator.stopped.comm_loss"
    GENERATOR_STOPPED_OVERRIDE = "generator.stopped.override"
    GENERATOR_STOPPED_ERROR = "generator.stopped.error"

    # Communication events
    COMMUNICATION_LOST = "communication.lost"
    COMMUNICATION_RESTORED = "communication.restored"

    # Override events
    OVERRIDE_ENABLED = "override.enabled"
    OVERRIDE_DISABLED = "override.disabled"

    # System events
    SYSTEM_BOOT = "system.boot"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_REBOOT = "system.reboot"

    # Health events
    HEALTH_WARNING = "health.warning"
    HEALTH_CRITICAL = "health.critical"
    HEALTH_RESTORED = "health.restored"

    # Test event
    TEST = "test"


class WebhookPayload(BaseModel):
    """Payload sent to webhook endpoints."""

    event: str = Field(description="Event type identifier")
    timestamp: int = Field(description="Unix timestamp of the event")
    source: str = Field(default="genmaster", description="Source of the event")
    data: dict[str, Any] = Field(
        default_factory=dict, description="Event-specific data"
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata including sequence number and version",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "event": "generator.started.victron",
                "timestamp": 1705320000,
                "source": "genmaster",
                "data": {"run_id": 42, "trigger": "victron"},
                "meta": {"sequence": 123, "version": "1.0.0"},
            }
        }


class WebhookConfig(BaseModel):
    """Webhook configuration for settings endpoint."""

    base_url: Optional[str] = Field(None, description="Webhook destination URL")
    secret: Optional[str] = Field(None, description="HMAC secret for signing")
    enabled: bool = Field(default=True, description="Whether webhooks are enabled")

    class Config:
        json_schema_extra = {
            "example": {
                "base_url": "http://n8n:5678/webhook/generator",
                "secret": "your-secret-key",
                "enabled": True,
            }
        }
