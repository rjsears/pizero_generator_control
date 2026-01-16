# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genslave/app/routers/relay.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 16th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Relay control API endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.relay import relay_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/relay", tags=["relay"])


# =========================================================================
# Schemas
# =========================================================================


class RelayState(BaseModel):
    """Current relay state."""

    relay_state: bool = Field(description="True if relay is ON")
    last_change: Optional[int] = Field(None, description="Unix timestamp of last change")
    change_count: int = Field(description="Total state changes since boot")
    mock_mode: bool = Field(description="Whether running in mock mode")
    armed: bool = Field(description="Whether automation is armed")
    armed_at: Optional[int] = Field(None, description="Unix timestamp when armed")


class RelayCommand(BaseModel):
    """Relay command request."""

    force: bool = Field(
        default=False,
        description="Force command execution even if not armed (for emergency use)",
    )


class RelayResponse(BaseModel):
    """Response from relay operations."""

    success: bool = Field(description="Whether the operation succeeded")
    relay_state: bool = Field(description="Current relay state after operation")
    message: str = Field(description="Human-readable status message")


class ArmRequest(BaseModel):
    """Request to arm/disarm automation."""

    source: str = Field(default="api", description="Source of the arm request")


class ArmResponse(BaseModel):
    """Response from arm/disarm operations."""

    success: bool = Field(description="Whether the operation succeeded")
    armed: bool = Field(description="Current armed state")
    message: str = Field(description="Human-readable status message")
    armed_at: Optional[int] = Field(None, description="Unix timestamp when armed")
    warning: Optional[str] = Field(None, description="Warning message if any")


# =========================================================================
# Endpoints
# =========================================================================


@router.get("/state", response_model=RelayState)
async def get_relay_state() -> RelayState:
    """
    Get current relay state.

    Returns the current state of the generator relay and arming status.
    """
    status = relay_service.get_status()
    return RelayState(**status)


@router.post("/on", response_model=RelayResponse)
async def relay_on(command: RelayCommand = RelayCommand()) -> RelayResponse:
    """
    Turn relay ON (start generator).

    Requires automation to be armed unless force=true.
    """
    if not relay_service.is_armed and not command.force:
        raise HTTPException(
            status_code=403,
            detail="Automation not armed - cannot turn relay ON",
        )

    success = relay_service.relay_on(force=command.force)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to turn relay ON")

    return RelayResponse(
        success=True,
        relay_state=relay_service.get_state(),
        message="Relay turned ON - generator starting",
    )


@router.post("/off", response_model=RelayResponse)
async def relay_off(command: RelayCommand = RelayCommand()) -> RelayResponse:
    """
    Turn relay OFF (stop generator).

    Always allowed for safety reasons, but logs if not armed.
    """
    success = relay_service.relay_off(force=command.force)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to turn relay OFF")

    return RelayResponse(
        success=True,
        relay_state=relay_service.get_state(),
        message="Relay turned OFF - generator stopping",
    )


# =========================================================================
# Arming Endpoints
# =========================================================================


@router.get("/arm", response_model=ArmResponse)
async def get_arm_status() -> ArmResponse:
    """Get current arming status."""
    status = relay_service.get_arm_status()
    return ArmResponse(
        success=True,
        armed=status["armed"],
        message="Armed" if status["armed"] else "Disarmed",
        armed_at=status.get("armed_at"),
    )


@router.post("/arm", response_model=ArmResponse)
async def arm_automation(request: ArmRequest = ArmRequest()) -> ArmResponse:
    """
    Arm the automation system.

    When armed, relay commands from GenMaster are executed.
    """
    result = relay_service.arm(source=request.source)
    return ArmResponse(**result)


@router.post("/disarm", response_model=ArmResponse)
async def disarm_automation(request: ArmRequest = ArmRequest()) -> ArmResponse:
    """
    Disarm the automation system.

    When disarmed, relay commands are logged but not executed.
    The relay is NOT automatically turned off - use /relay/off if needed.
    """
    result = relay_service.disarm(source=request.source)
    return ArmResponse(
        success=result["success"],
        armed=result["armed"],
        message=result["message"],
        warning=result.get("warning"),
    )
