# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/dev.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Development API endpoints for testing GPIO simulation."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings

router = APIRouter()


class MockGPIORequest(BaseModel):
    """Request to set mock GPIO state."""
    active: bool


class MockGPIOResponse(BaseModel):
    """Response from mock GPIO operations."""
    success: bool
    gpio_pin: int = 17
    current_state: bool
    mock_mode: bool
    message: str


def get_gpio_monitor():
    """Get GPIO monitor from app state."""
    from app.main import gpio_monitor
    return gpio_monitor


def require_mock_mode(gpio_monitor=Depends(get_gpio_monitor)):
    """Dependency that ensures we're in mock mode."""
    if gpio_monitor is None:
        raise HTTPException(
            status_code=503,
            detail="GPIO monitor not initialized"
        )
    if not gpio_monitor.mock_mode:
        raise HTTPException(
            status_code=403,
            detail="Mock GPIO endpoints only available in mock mode (non-Pi systems)"
        )
    return gpio_monitor


@router.get("/gpio/status", response_model=MockGPIOResponse)
async def get_mock_gpio_status(
    gpio_monitor=Depends(get_gpio_monitor),
) -> MockGPIOResponse:
    """
    Get current GPIO17 mock status.

    Works in both real and mock mode to show current state.
    """
    if gpio_monitor is None:
        raise HTTPException(status_code=503, detail="GPIO monitor not initialized")

    return MockGPIOResponse(
        success=True,
        gpio_pin=gpio_monitor.gpio_pin,
        current_state=gpio_monitor.current_state,
        mock_mode=gpio_monitor.mock_mode,
        message=f"GPIO{gpio_monitor.gpio_pin} is {'ACTIVE' if gpio_monitor.current_state else 'INACTIVE'} "
                f"({'mock' if gpio_monitor.mock_mode else 'real'} mode)"
    )


@router.post("/gpio/set", response_model=MockGPIOResponse)
async def set_mock_gpio(
    request: MockGPIORequest,
    gpio_monitor=Depends(require_mock_mode),
) -> MockGPIOResponse:
    """
    Set mock GPIO17 state to simulate Victron/Cerbo signal.

    Only available in mock mode (non-Pi systems).

    - active=true: Simulate generator start signal from Cerbo
    - active=false: Simulate signal off (generator not needed)
    """
    try:
        gpio_monitor.mock_set_signal(request.active)
        return MockGPIOResponse(
            success=True,
            gpio_pin=gpio_monitor.gpio_pin,
            current_state=gpio_monitor.current_state,
            mock_mode=True,
            message=f"Mock GPIO{gpio_monitor.gpio_pin} set to {'ACTIVE' if request.active else 'INACTIVE'}"
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/gpio/toggle", response_model=MockGPIOResponse)
async def toggle_mock_gpio(
    gpio_monitor=Depends(require_mock_mode),
) -> MockGPIOResponse:
    """
    Toggle mock GPIO17 state.

    Only available in mock mode (non-Pi systems).
    Convenience endpoint to flip the current state.
    """
    try:
        new_state = gpio_monitor.mock_toggle_signal()
        return MockGPIOResponse(
            success=True,
            gpio_pin=gpio_monitor.gpio_pin,
            current_state=new_state,
            mock_mode=True,
            message=f"Mock GPIO{gpio_monitor.gpio_pin} toggled to {'ACTIVE' if new_state else 'INACTIVE'}"
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/gpio/pulse", response_model=MockGPIOResponse)
async def pulse_mock_gpio(
    gpio_monitor=Depends(require_mock_mode),
) -> MockGPIOResponse:
    """
    Pulse mock GPIO17 - activate briefly then deactivate.

    Only available in mock mode (non-Pi systems).
    Simulates a momentary signal from Cerbo.
    """
    import asyncio

    try:
        # Activate
        gpio_monitor.mock_set_signal(True)
        await asyncio.sleep(0.5)  # Hold for 500ms
        # Deactivate
        gpio_monitor.mock_set_signal(False)

        return MockGPIOResponse(
            success=True,
            gpio_pin=gpio_monitor.gpio_pin,
            current_state=False,
            mock_mode=True,
            message=f"Mock GPIO{gpio_monitor.gpio_pin} pulsed (active for 500ms)"
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/info")
async def get_dev_info(
    gpio_monitor=Depends(get_gpio_monitor),
) -> dict:
    """
    Get development environment info.

    Shows mock mode status and available dev endpoints.
    """
    is_mock = gpio_monitor.mock_mode if gpio_monitor else settings.is_mock_gpio

    return {
        "mock_mode": is_mock,
        "gpio_pin": gpio_monitor.gpio_pin if gpio_monitor else 17,
        "gpio_running": gpio_monitor.is_running if gpio_monitor else False,
        "gpio_current_state": gpio_monitor.current_state if gpio_monitor else None,
        "endpoints": {
            "GET /api/dev/gpio/status": "Get current GPIO state",
            "POST /api/dev/gpio/set": "Set GPIO state (mock mode only)",
            "POST /api/dev/gpio/toggle": "Toggle GPIO state (mock mode only)",
            "POST /api/dev/gpio/pulse": "Pulse GPIO (mock mode only)",
        } if is_mock else {
            "message": "Mock GPIO endpoints disabled in production (real GPIO mode)"
        }
    }
