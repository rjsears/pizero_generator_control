# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genslave/app/routers/health.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 16th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Health check and heartbeat API endpoints."""

import logging
import time
from typing import Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import settings
from app.services.failsafe import failsafe_monitor
from app.services.relay import relay_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


# =========================================================================
# Schemas
# =========================================================================


class HealthCheck(BaseModel):
    """Basic health check response."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        description="Overall health status"
    )
    version: str = Field(description="Application version")
    uptime_seconds: int = Field(description="System uptime in seconds")
    relay_state: bool = Field(description="Current relay state")
    failsafe_active: bool = Field(description="Whether failsafe has been triggered")
    armed: bool = Field(description="Whether automation is armed")
    mock_mode: bool = Field(description="Whether running in mock HAT mode")


class HeartbeatRequest(BaseModel):
    """Heartbeat request from GenMaster."""

    timestamp: int = Field(description="Unix timestamp from GenMaster")
    generator_running: bool = Field(
        description="GenMaster's view of generator state"
    )
    command: Literal["start", "stop", "none"] = Field(
        default="none",
        description="Command to execute (start/stop relay)",
    )
    armed: Optional[bool] = Field(
        None,
        description="GenMaster armed state (for sync)",
    )
    heartbeat_interval: Optional[int] = Field(
        None,
        description="GenMaster's heartbeat interval in seconds (used to calculate failsafe timeout)",
    )


class HeartbeatResponse(BaseModel):
    """Heartbeat response to GenMaster."""

    relay_state: bool = Field(description="Current relay state")
    uptime: int = Field(description="System uptime in seconds")
    failsafe_active: bool = Field(description="Whether failsafe is triggered")
    heartbeat_count: int = Field(description="Total heartbeats received")
    armed: bool = Field(description="Whether automation is armed")


class FailsafeStatus(BaseModel):
    """Failsafe monitor status."""

    running: bool = Field(description="Whether monitor is running")
    last_heartbeat: Optional[int] = Field(
        None, description="Unix timestamp of last heartbeat"
    )
    seconds_since_heartbeat: Optional[int] = Field(
        None, description="Seconds since last heartbeat"
    )
    heartbeat_count: int = Field(description="Total heartbeats received")
    failsafe_triggered: bool = Field(description="Whether failsafe is active")
    failsafe_triggered_at: Optional[int] = Field(
        None, description="When failsafe was triggered"
    )
    timeout_seconds: int = Field(description="Failsafe timeout threshold")
    heartbeat_interval: Optional[int] = Field(
        None, description="GenMaster's heartbeat interval in seconds"
    )
    timeout_source: Literal["genmaster", "config"] = Field(
        default="config",
        description="Source of timeout value (genmaster=dynamic, config=default)"
    )


# =========================================================================
# Endpoints
# =========================================================================


@router.get("/api/health", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    """
    Basic health check endpoint.

    Used by GenMaster and load balancers to verify GenSlave is responding.
    """
    status = "healthy"
    warnings = []

    # Check failsafe state
    failsafe_status = failsafe_monitor.get_status()
    if failsafe_status["failsafe_triggered"]:
        status = "degraded"
        warnings.append("Failsafe triggered")

    # Check HAT availability
    if relay_service.is_mock_mode:
        if settings.MOCK_HAT_MODE:
            pass  # Expected in mock mode
        else:
            status = "degraded"
            warnings.append("Automation Hat not detected")

    return HealthCheck(
        status=status,
        version=settings.APP_VERSION,
        uptime_seconds=_get_uptime(),
        relay_state=relay_service.get_state(),
        failsafe_active=failsafe_status["failsafe_triggered"],
        armed=relay_service.is_armed,
        mock_mode=relay_service.is_mock_mode,
    )


@router.post("/api/heartbeat", response_model=HeartbeatResponse)
async def receive_heartbeat(request: HeartbeatRequest) -> HeartbeatResponse:
    """
    Receive heartbeat from GenMaster.

    This endpoint:
    1. Records the heartbeat timestamp
    2. Processes any command (start/stop)
    3. Optionally syncs armed state from GenMaster
    4. Returns current status

    The failsafe monitor uses this to track GenMaster connectivity.
    """
    # NOTE: We intentionally do NOT sync armed state from GenMaster heartbeat.
    # GenSlave's relay armed state is controlled independently via /api/relay/arm
    # and /api/relay/disarm endpoints. The heartbeat's "armed" field is informational
    # only - it tells GenSlave what GenMaster's automation state is, but does not
    # change GenSlave's relay armed state.

    # Record heartbeat and process command
    response = failsafe_monitor.record_heartbeat({
        "timestamp": request.timestamp,
        "generator_running": request.generator_running,
        "command": request.command,
        "heartbeat_interval": request.heartbeat_interval,
    })

    return HeartbeatResponse(**response)


@router.get("/api/failsafe", response_model=FailsafeStatus)
async def get_failsafe_status() -> FailsafeStatus:
    """
    Get failsafe monitor status.

    Shows the current state of the failsafe mechanism including
    heartbeat tracking and trigger status.
    """
    status = failsafe_monitor.get_status()
    return FailsafeStatus(**status)


def _get_uptime() -> int:
    """Get system uptime in seconds."""
    try:
        with open("/proc/uptime", "r") as f:
            return int(float(f.read().split()[0]))
    except Exception:
        return 0
