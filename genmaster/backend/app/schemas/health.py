# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/schemas/health.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Health check related Pydantic schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class HealthCheck(BaseModel):
    """Basic health check response."""

    status: Literal["ok", "degraded", "error"] = Field(
        description="Overall health status"
    )
    timestamp: int = Field(description="Unix timestamp of the check")
    version: str = Field(description="Application version")


class SlaveHealth(BaseModel):
    """GenSlave health status."""

    connection_status: Literal["connected", "disconnected", "unknown"] = Field(
        description="Current connection status to GenSlave"
    )
    last_heartbeat_sent: Optional[int] = Field(
        None, description="Unix timestamp of last heartbeat sent"
    )
    last_heartbeat_received: Optional[int] = Field(
        None, description="Unix timestamp of last heartbeat received"
    )
    missed_heartbeat_count: int = Field(
        description="Number of consecutive missed heartbeats"
    )
    relay_state: Optional[bool] = Field(
        None, description="Current state of the GenSlave relay"
    )
    latency_ms: Optional[float] = Field(
        None, description="Last measured round-trip latency in milliseconds"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "connection_status": "connected",
                "last_heartbeat_sent": 1705320000,
                "last_heartbeat_received": 1705320001,
                "missed_heartbeat_count": 0,
                "relay_state": False,
                "latency_ms": 45.2,
            }
        }


class HeartbeatTestResponse(BaseModel):
    """Response from a test heartbeat."""

    success: bool = Field(description="Whether the heartbeat was successful")
    latency_ms: Optional[float] = Field(
        None, description="Round-trip latency in milliseconds"
    )
    slave_status: Optional[dict] = Field(
        None, description="Status returned by GenSlave"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class WebhookTestResponse(BaseModel):
    """Response from a test webhook."""

    success: bool = Field(description="Whether the webhook was sent successfully")
    status_code: Optional[int] = Field(None, description="HTTP status code returned")
    response_time_ms: Optional[float] = Field(
        None, description="Response time in milliseconds"
    )
    error: Optional[str] = Field(None, description="Error message if failed")
