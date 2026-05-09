# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/schemas/config.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Configuration-related Pydantic schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class ConfigResponse(BaseModel):
    """System configuration response."""

    # Heartbeat Settings
    heartbeat_interval_seconds: int = Field(
        description="Interval between heartbeats in seconds"
    )
    heartbeat_failure_threshold: int = Field(
        description="Number of missed heartbeats before marking disconnected"
    )

    # GenSlave Connection
    slave_api_url: str = Field(description="GenSlave API URL")
    slave_api_secret: str = Field(description="GenSlave API secret for authentication")
    genslave_ip: Optional[str] = Field(None, description="GenSlave IP address")
    genslave_hostname: str = Field(description="GenSlave hostname for /etc/hosts")

    # Webhook Settings
    webhook_base_url: Optional[str] = Field(None, description="Webhook destination URL")
    webhook_enabled: bool = Field(description="Whether webhooks are enabled")
    # Note: webhook_secret is not exposed in responses for security

    # Health Thresholds
    temp_warning_celsius: int = Field(description="Temperature warning threshold")
    temp_critical_celsius: int = Field(description="Temperature critical threshold")
    disk_warning_percent: int = Field(description="Disk usage warning threshold")
    disk_critical_percent: int = Field(description="Disk usage critical threshold")
    ram_warning_percent: int = Field(description="RAM usage warning threshold")

    # Networking
    tailscale_hostname: Optional[str] = Field(None, description="Tailscale hostname")
    tailscale_ip: Optional[str] = Field(None, description="Tailscale IP address")
    cloudflare_enabled: bool = Field(description="Whether Cloudflare tunnel is enabled")
    cloudflare_hostname: Optional[str] = Field(None, description="Cloudflare hostname")

    # SSL Configuration
    ssl_enabled: bool = Field(description="Whether SSL is enabled")
    ssl_domain: Optional[str] = Field(None, description="SSL domain")

    # Event Log
    event_log_retention_days: int = Field(
        description="Number of days to retain event logs"
    )

    # Run Time Limits
    runtime_limits_enabled: bool = Field(
        description="Whether runtime limits feature is enabled"
    )
    min_run_minutes: int = Field(
        description="Minimum run time in minutes before generator can be stopped"
    )
    max_run_minutes: int = Field(
        description="Maximum run time in minutes before automatic shutdown"
    )
    max_runtime_action: str = Field(
        description="Action when max runtime reached: 'manual_reset' or 'cooldown'"
    )
    cooldown_duration_minutes: int = Field(
        description="Duration in minutes for cooldown period before restart allowed"
    )

    class Config:
        from_attributes = True


class ConfigUpdateRequest(BaseModel):
    """Request to update system configuration."""

    # Heartbeat Settings
    heartbeat_interval_seconds: Optional[int] = Field(None, ge=10, le=300)
    heartbeat_failure_threshold: Optional[int] = Field(None, ge=1, le=10)

    # GenSlave Connection
    slave_api_url: Optional[str] = Field(None, max_length=255)
    slave_api_secret: Optional[str] = Field(None, max_length=255)
    genslave_ip: Optional[str] = Field(None, max_length=45)
    genslave_hostname: Optional[str] = Field(None, max_length=50)

    # Webhook Settings
    webhook_base_url: Optional[str] = Field(None, max_length=255)
    webhook_secret: Optional[str] = Field(None, max_length=255)
    webhook_enabled: Optional[bool] = None

    # Health Thresholds
    temp_warning_celsius: Optional[int] = Field(None, ge=40, le=90)
    temp_critical_celsius: Optional[int] = Field(None, ge=50, le=100)
    disk_warning_percent: Optional[int] = Field(None, ge=50, le=95)
    disk_critical_percent: Optional[int] = Field(None, ge=60, le=99)
    ram_warning_percent: Optional[int] = Field(None, ge=50, le=95)

    # Networking
    tailscale_hostname: Optional[str] = Field(None, max_length=50)
    tailscale_ip: Optional[str] = Field(None, max_length=45)
    cloudflare_enabled: Optional[bool] = None
    cloudflare_hostname: Optional[str] = Field(None, max_length=255)

    # SSL Configuration
    ssl_enabled: Optional[bool] = None
    ssl_domain: Optional[str] = Field(None, max_length=255)
    ssl_email: Optional[str] = Field(None, max_length=255)
    ssl_dns_provider: Optional[str] = Field(None, max_length=50)

    # Event Log
    event_log_retention_days: Optional[int] = Field(None, ge=1, le=365)

    # Run Time Limits
    runtime_limits_enabled: Optional[bool] = None
    min_run_minutes: Optional[int] = Field(None, ge=1, le=60)
    max_run_minutes: Optional[int] = Field(None, ge=1, le=1440)
    max_runtime_action: Optional[str] = Field(None, pattern=r"^(manual_reset|cooldown)$")
    cooldown_duration_minutes: Optional[int] = Field(None, ge=1, le=1440)
