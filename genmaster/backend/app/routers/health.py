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


def get_heartbeat_service():
    """Get heartbeat service from app state."""
    from app.main import heartbeat_service

    return heartbeat_service


def get_webhook_service():
    """Get webhook service from app state."""
    from app.main import webhook_service

    return webhook_service


def get_slave_client():
    """Get slave client from app state."""
    from app.main import slave_client

    return slave_client


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


@router.post("/test/heartbeat", response_model=HeartbeatTestResponse)
async def test_heartbeat(
    heartbeat_service=Depends(get_heartbeat_service),
) -> HeartbeatTestResponse:
    """
    Send a test heartbeat to GenSlave.

    Useful for verifying connectivity without waiting for scheduled heartbeat.
    """
    result = await heartbeat_service.send_test_heartbeat()
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
