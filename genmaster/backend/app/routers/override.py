# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/override.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Manual override API endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.schemas import (
    OverrideDisableResponse,
    OverrideEnableRequest,
    OverrideStatus,
)

router = APIRouter()


def get_state_machine():
    """Get state machine from app state."""
    from app.main import state_machine

    return state_machine


@router.get("/status", response_model=OverrideStatus)
async def get_override_status(
    state_machine=Depends(get_state_machine),
) -> OverrideStatus:
    """
    Get current override status.

    Returns whether override is enabled and its type (force_run/force_stop).
    """
    return await state_machine.get_override_status()


@router.post("/enable", response_model=OverrideStatus)
async def enable_override(
    request: OverrideEnableRequest,
    state_machine=Depends(get_state_machine),
) -> OverrideStatus:
    """
    Enable manual override.

    Types:
    - force_run: Keep generator running regardless of Victron signal
    - force_stop: Keep generator stopped regardless of Victron signal
    """
    try:
        await state_machine.enable_override(request.override_type)
        return await state_machine.get_override_status()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/disable", response_model=OverrideDisableResponse)
async def disable_override(
    state_machine=Depends(get_state_machine),
) -> OverrideDisableResponse:
    """
    Disable manual override.

    Returns generator control to automatic mode.
    """
    previous_type = await state_machine.disable_override()
    return OverrideDisableResponse(
        success=True,
        message="Override disabled",
        previous_type=previous_type,
    )
