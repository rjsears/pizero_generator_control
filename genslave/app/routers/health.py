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
from typing import Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.failsafe import failsafe_monitor
from app.services.hardware_safety import hardware_safety_monitor
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
    physical_safety_engaged: bool = Field(
        default=False,
        description=(
            "True when the hardware EPO (E-stop) at GenSlave is currently "
            "pressed. The relay is forced OFF in this state and cannot be "
            "started by any software command until the operator physically "
            "releases the switch."
        ),
    )


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
    physical_safety_engaged: bool = Field(
        default=False,
        description="True when the hardware EPO at GenSlave is currently pressed",
    )


class HardwareSafetyStatus(BaseModel):
    """Hardware safety (EPO) monitor status — dedicated diagnostic surface
    for GenMaster's UI and the operator-facing manual page."""

    running: bool = Field(description="Whether the safety polling loop is running")
    available: bool = Field(
        description=(
            "Whether the Auto Hat Mini library is responding. False in mock "
            "mode or when the HAT is not present; engaged will always be False."
        )
    )
    enabled: bool = Field(
        description="Whether the monitor is enabled via HARDWARE_SAFETY_ENABLED config",
    )
    engaged: bool = Field(
        description="True when the EPO is currently pressed (debounced)",
    )
    engaged_at: Optional[int] = Field(
        None,
        description="Unix timestamp of the most recent engagement (None if never engaged)",
    )
    released_at: Optional[int] = Field(
        None,
        description="Unix timestamp of the most recent release (None if never released)",
    )
    engagement_count: int = Field(
        description="Total number of debounced engagement events since boot",
    )
    raw_input: bool = Field(
        description=(
            "Raw most-recent read of Auto Hat Mini IN1. Differs from engaged "
            "only during the debounce window."
        ),
    )


# =========================================================================
# Endpoints
# =========================================================================


# Note: /api/health is defined in main.py as a public endpoint (no auth required)
# This allows GenMaster setup and load balancers to check connectivity without API key


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
    # Sync armed state from GenMaster if provided and mismatched
    if request.armed is not None:
        if request.armed and not relay_service.is_armed:
            relay_service.arm(source="genmaster_sync")
            logger.info("Armed via GenMaster heartbeat sync")
        elif not request.armed and relay_service.is_armed:
            relay_service.disarm(source="genmaster_sync")
            logger.info("Disarmed via GenMaster heartbeat sync")

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


@router.get("/api/safety", response_model=HardwareSafetyStatus)
async def get_hardware_safety_status() -> HardwareSafetyStatus:
    """
    Get hardware safety (EPO) monitor status.

    Dedicated endpoint for the EPO interlock state on Auto Hat Mini IN1.
    Used by GenMaster for UI display ("E-Stop Triggered" banner, system
    status card) and by diagnostics. The `engaged` flag is also surfaced
    via heartbeat reply, /api/health, /api/relay/state, and /api/failsafe
    so callers can choose the most convenient path.
    """
    return HardwareSafetyStatus(**hardware_safety_monitor.get_status())


def _get_uptime() -> int:
    """Get system uptime in seconds."""
    try:
        with open("/proc/uptime", "r") as f:
            return int(float(f.read().split()[0]))
    except Exception:
        return 0
