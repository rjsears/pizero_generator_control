# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/health.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Health check API endpoints."""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.schemas import (
    HealthCheck,
    HeartbeatTestResponse,
    SlaveHealth,
    WebhookTestResponse,
)

router = APIRouter()


def get_state_machine():
    """Get state machine from app state."""
    from app.main import state_machine

    return state_machine


def get_webhook_service():
    """Get webhook service from app state."""
    from app.main import webhook_service

    return webhook_service


async def get_slave_client():
    """Create a SlaveClient with config from database."""
    from app.database import AsyncSessionLocal
    from app.models import Config
    from app.services.slave_client import SlaveClient
    from sqlalchemy.future import select

    # Load config from database to get current URL and secret
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Config).where(Config.id == 1))
        config = result.scalar_one_or_none()

    if config:
        # Use IP directly in URL if available (no /etc/hosts needed, no restart required)
        if config.genslave_ip:
            base_url = f"http://{config.genslave_ip}:8001"
        else:
            base_url = config.slave_api_url
        return SlaveClient(
            base_url=base_url,
            secret=config.slave_api_secret,
        )
    else:
        # Fallback to settings if no config in database
        from app.config import settings
        return SlaveClient(
            base_url=settings.slave_api_url,
            secret=settings.slave_api_secret,
        )


@router.get("", response_model=HealthCheck)
@router.get("/", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    """
    Basic health check endpoint.

    Returns OK if the service is running.
    """
    return HealthCheck(
        status="ok",
        timestamp=int(time.time()),
        version="1.0.0",
    )


@router.get("/slave", response_model=SlaveHealth)
async def get_slave_health(
    state_machine=Depends(get_state_machine),
) -> SlaveHealth:
    """
    Get GenSlave health status.

    Returns connection status, heartbeat timing, and relay state.
    """
    return await state_machine.get_slave_health()


@router.get("/slave/details")
async def get_slave_details(
    slave_client=Depends(get_slave_client),
) -> dict[str, Any]:
    """
    Get detailed GenSlave system information.

    Proxies to GenSlave's /api/system endpoint and returns full system metrics
    including CPU, RAM, disk, temperature, network interfaces, and WiFi signal.
    """
    response = await slave_client.get_system_health()

    if not response.success:
        raise HTTPException(
            status_code=502,
            detail=response.error or "Failed to connect to GenSlave",
        )

    return response.data


@router.post("/test-slave")
async def test_slave_connection(
    slave_client=Depends(get_slave_client),
) -> dict[str, Any]:
    """
    Test connection to GenSlave.

    Makes a simple request to GenSlave and returns success/failure with latency.
    """
    response = await slave_client.get_system_health()

    return {
        "success": response.success,
        "latency_ms": response.latency_ms,
        "error": response.error,
        "response_time_ms": response.latency_ms,  # Alias for frontend compatibility
    }


@router.get("/slave/health")
async def get_slave_health_status(
    slave_client=Depends(get_slave_client),
) -> dict[str, Any]:
    """
    Get GenSlave quick health status.

    Returns relay_state, failsafe_active, armed, mock_mode.
    """
    response = await slave_client.get_health_status()

    if not response.success:
        raise HTTPException(
            status_code=502,
            detail=response.error or "Failed to get health status from GenSlave",
        )

    return response.data


@router.get("/slave/failsafe")
async def get_slave_failsafe(
    slave_client=Depends(get_slave_client),
) -> dict[str, Any]:
    """
    Get GenSlave failsafe status.

    Returns failsafe monitoring details.
    """
    response = await slave_client.get_failsafe_status()

    if not response.success:
        raise HTTPException(
            status_code=502,
            detail=response.error or "Failed to get failsafe status from GenSlave",
        )

    return response.data


@router.get("/slave/system")
async def get_slave_full_system(
    slave_client=Depends(get_slave_client),
) -> dict[str, Any]:
    """
    Get GenSlave full system information.

    Returns CPU, RAM, disk, temp, uptime, network interfaces, WiFi.
    """
    response = await slave_client.get_system_health()

    if not response.success:
        raise HTTPException(
            status_code=502,
            detail=response.error or "Failed to get system info from GenSlave",
        )

    return response.data


# =========================================================================
# Relay Arm/Disarm Endpoints (proxied to GenSlave)
# =========================================================================


@router.post("/relay/arm")
async def arm_relay(
    slave_client=Depends(get_slave_client),
    state_machine=Depends(get_state_machine),
) -> dict[str, Any]:
    """
    Arm the relay on GenSlave.

    Enables remote generator control via relay.
    Also updates GenMaster's database to track the armed state.
    """
    response = await slave_client.arm_relay()

    if not response.success:
        raise HTTPException(
            status_code=502,
            detail=response.error or "Failed to arm relay on GenSlave",
        )

    # Update GenMaster's database to track the armed state
    # This ensures heartbeat sync sends armed=True
    await state_machine.set_armed_state(True)

    # Update the slave status cache immediately
    service = get_slave_status_service()
    await service.update_relay_state(armed=True)

    return {
        "success": True,
        "armed": True,
        "message": "Relay armed successfully",
    }


@router.post("/relay/disarm")
async def disarm_relay(
    slave_client=Depends(get_slave_client),
    state_machine=Depends(get_state_machine),
) -> dict[str, Any]:
    """
    Disarm the relay on GenSlave.

    Disables remote generator control via relay.
    Also updates GenMaster's database to track the disarmed state.
    """
    response = await slave_client.disarm_relay()

    if not response.success:
        raise HTTPException(
            status_code=502,
            detail=response.error or "Failed to disarm relay on GenSlave",
        )

    # Update GenMaster's database to track the disarmed state
    await state_machine.set_armed_state(False)

    # Update the slave status cache immediately
    service = get_slave_status_service()
    await service.update_relay_state(armed=False)

    return {
        "success": True,
        "armed": False,
        "message": "Relay disarmed successfully",
    }


@router.get("/relay/state")
async def get_relay_arm_state(
    slave_client=Depends(get_slave_client),
) -> dict[str, Any]:
    """
    Get current relay arm state from GenSlave.

    Returns whether the relay is armed or disarmed.
    """
    response = await slave_client.get_relay_state()

    if not response.success:
        # Default to disarmed if we can't reach GenSlave
        return {
            "armed": False,
            "error": response.error or "Failed to get relay state from GenSlave",
        }

    # The GenSlave /api/relay/state returns { "armed": bool, "relay_on": bool }
    return {
        "armed": response.data.get("armed", False) if response.data else False,
        "relay_on": response.data.get("relay_on", False) if response.data else False,
    }


# =========================================================================
# Cached Slave Status Endpoints (instant response from background polling)
# =========================================================================


def get_slave_status_service():
    """Get the slave status service singleton."""
    from app.services.slave_status_service import get_slave_status_service as _get_service
    return _get_service()


def _wrap_cached_response(
    data: dict[str, Any],
    service,
) -> dict[str, Any]:
    """Wrap cached data with metadata for the response."""
    cache = service.cache
    now = int(time.time())
    cache_age = now - cache.last_successful_fetch if cache.last_successful_fetch else None

    return {
        "data": data,
        "is_online": cache.is_online,
        "is_stale": cache_age is not None and cache_age > service.STALE_THRESHOLD,
        "cache_age_seconds": cache_age,
        "last_error": cache.last_error,
    }


@router.get("/slave/cached")
async def get_slave_cached_status() -> dict[str, Any]:
    """
    Get all cached GenSlave status data.

    Returns instant response from background polling cache.
    Includes health, relay state, failsafe, and system info.
    """
    service = get_slave_status_service()
    return service.get_combined_status()


@router.get("/slave/cached/health")
async def get_slave_cached_health() -> dict[str, Any]:
    """
    Get cached GenSlave health status.

    Returns instant response from background polling cache.
    """
    service = get_slave_status_service()
    return _wrap_cached_response(service.get_health(), service)


@router.get("/slave/cached/relay")
async def get_slave_cached_relay() -> dict[str, Any]:
    """
    Get cached GenSlave relay state.

    Returns instant response from background polling cache.
    """
    service = get_slave_status_service()
    return _wrap_cached_response(service.get_relay_state(), service)


@router.get("/slave/cached/failsafe")
async def get_slave_cached_failsafe() -> dict[str, Any]:
    """
    Get cached GenSlave failsafe status.

    Returns instant response from background polling cache.
    """
    service = get_slave_status_service()
    return _wrap_cached_response(service.get_failsafe(), service)


@router.get("/slave/cached/system")
async def get_slave_cached_system() -> dict[str, Any]:
    """
    Get cached GenSlave system info.

    Returns instant response from background polling cache.
    Note: System info is polled less frequently (every 30s).
    """
    service = get_slave_status_service()
    return _wrap_cached_response(service.get_system_info(), service)


@router.post("/slave/cached/refresh")
async def refresh_slave_cache() -> dict[str, Any]:
    """
    Force an immediate refresh of all cached GenSlave data.

    Use sparingly - the background polling should be sufficient for most cases.
    """
    service = get_slave_status_service()
    return await service.force_refresh()


@router.post("/rotate-api-key")
async def rotate_api_key(
    request: dict[str, Any],
    slave_client=Depends(get_slave_client),
) -> dict[str, Any]:
    """
    Rotate the API key on both GenSlave and GenMaster.

    1. Calls GenSlave to rotate the key
    2. If successful, updates GenMaster's database with the new key

    Request body: { "new_key": "<new-api-key-min-16-chars>" }
    """
    new_key = request.get("new_key", "")

    if not new_key or len(new_key) < 16:
        raise HTTPException(
            status_code=400,
            detail="New API key must be at least 16 characters",
        )

    # Step 1: Rotate the key on GenSlave
    response = await slave_client.rotate_api_key(new_key)

    if not response.success:
        raise HTTPException(
            status_code=502,
            detail=response.error or "Failed to rotate API key on GenSlave",
        )

    # Step 2: Update GenMaster's database with the new key
    from app.database import AsyncSessionLocal
    from app.models import Config
    from sqlalchemy.future import select

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Config).where(Config.id == 1))
            config = result.scalar_one_or_none()
            if config:
                config.slave_api_secret = new_key
                await db.commit()
    except Exception as e:
        # GenSlave key was rotated but GenMaster failed to update
        # This is a bad state - log it and return error with instructions
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to update GenMaster config after GenSlave key rotation: {e}")
        raise HTTPException(
            status_code=500,
            detail="GenSlave key rotated but failed to update GenMaster. "
                   f"Manually set slave_api_secret to '{new_key}' in GenMaster config.",
        )

    return {
        "success": True,
        "message": "API key rotated successfully on both GenSlave and GenMaster",
    }


@router.post("/test/heartbeat", response_model=HeartbeatTestResponse)
async def test_heartbeat() -> HeartbeatTestResponse:
    """
    Send a test heartbeat to GenSlave.

    Useful for verifying connectivity without waiting for scheduled heartbeat.
    Uses the unified SlaveStatusService which handles all GenSlave communication.
    """
    service = get_slave_status_service()
    result = await service.send_test_heartbeat()
    return HeartbeatTestResponse(
        success=result.success,
        latency_ms=result.latency_ms,
        slave_status=result.slave_status,
        error=result.error,
    )


@router.post("/test/webhook", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_service=Depends(get_webhook_service),
) -> WebhookTestResponse:
    """
    Send a test webhook notification.

    Useful for verifying webhook configuration.
    """
    result = await webhook_service.send_test()
    return WebhookTestResponse(
        success=result.success,
        status_code=result.status_code,
        response_time_ms=result.response_time_ms,
        error=result.error,
    )
