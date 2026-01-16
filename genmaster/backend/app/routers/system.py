# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/system.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""System information API endpoints."""

import asyncio
import platform
import time

from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.schemas import (
    ArmRequest,
    ArmResponse,
    AutomationArmStatus,
    CombinedSystemHealth,
    FullSystemStatus,
    SystemHealth,
    VictronStatus,
)
from app.utils.system_info import get_system_health

router = APIRouter()


def get_state_machine():
    """Get state machine from app state."""
    from app.main import state_machine

    return state_machine


def get_gpio_monitor():
    """Get GPIO monitor from app state."""
    from app.main import gpio_monitor

    return gpio_monitor


@router.get("", response_model=SystemHealth)
@router.get("/", response_model=SystemHealth)
async def get_system_info() -> SystemHealth:
    """
    Get GenMaster system health metrics.

    Returns CPU, RAM, disk, temperature, and uptime.
    """
    return await get_system_health()


@router.get("/combined", response_model=CombinedSystemHealth)
async def get_combined_system_info(
    state_machine=Depends(get_state_machine),
) -> CombinedSystemHealth:
    """
    Get combined health for GenMaster and GenSlave.
    """
    # Get GenMaster health
    master_health = await get_system_health()

    # Try to get GenSlave health
    slave_health = None
    try:
        from app.services.slave_client import SlaveClient

        client = SlaveClient()
        response = await client.get_system_health()
        await client.close()

        if response.success and response.data:
            # Convert slave response to SystemHealth
            data = response.data
            slave_health = SystemHealth(
                hostname=data.get("hostname", "genslave"),
                platform=data.get("platform", "linux"),
                cpu_percent=data.get("cpu_percent", 0),
                ram_total_mb=data.get("ram_total_mb", 0),
                ram_used_mb=data.get("ram_used_mb", 0),
                ram_percent=data.get("ram_percent", 0),
                disk_total_gb=data.get("disk_total_gb", 0),
                disk_used_gb=data.get("disk_used_gb", 0),
                disk_percent=data.get("disk_percent", 0),
                temperature_celsius=data.get("temperature_celsius"),
                uptime_seconds=data.get("uptime_seconds", 0),
                status=data.get("status", "unknown"),
                warnings=data.get("warnings", []),
            )
    except Exception:
        pass

    # Determine overall status
    if slave_health is None:
        overall = "warning" if master_health.status == "healthy" else master_health.status
    elif master_health.status == "critical" or slave_health.status == "critical":
        overall = "critical"
    elif master_health.status == "warning" or slave_health.status == "warning":
        overall = "warning"
    else:
        overall = "healthy"

    return CombinedSystemHealth(
        genmaster=master_health,
        genslave=slave_health,
        overall_status=overall,
    )


@router.get("/victron", response_model=VictronStatus)
async def get_victron_status(
    state_machine=Depends(get_state_machine),
    gpio_monitor=Depends(get_gpio_monitor),
) -> VictronStatus:
    """
    Get Victron relay input status.

    Returns current GPIO17 state and last change time.
    """
    status = await state_machine.get_victron_status(
        mock_mode=gpio_monitor.mock_mode if gpio_monitor else settings.is_mock_gpio
    )
    return status


@router.get("/status", response_model=FullSystemStatus)
async def get_full_status(
    state_machine=Depends(get_state_machine),
) -> FullSystemStatus:
    """
    Get complete system status.

    Returns generator, victron, slave health, override, and system metrics.
    """
    system_health = await get_system_health()
    return await state_machine.get_full_status(system_health)


@router.get("/info")
async def get_system_metadata() -> dict:
    """
    Get system metadata.

    Returns hostname, platform, Python version, etc.
    """
    import socket

    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "platform_release": platform.release(),
        "python_version": platform.python_version(),
        "architecture": platform.machine(),
        "timestamp": int(time.time()),
    }


@router.post("/reboot")
async def reboot_system(
    state_machine=Depends(get_state_machine),
) -> dict:
    """
    Initiate system reboot.

    Logs event and sends webhook before rebooting.
    Reboot has a 5-second delay.
    """
    # Log event
    await state_machine.log_event("SYSTEM_REBOOT", {"initiated_by": "api"})

    # Schedule reboot in background
    async def do_reboot():
        await asyncio.sleep(5)
        import subprocess

        subprocess.run(["sudo", "reboot"])

    asyncio.create_task(do_reboot())

    return {
        "success": True,
        "message": "Reboot initiated, system will restart in 5 seconds",
    }


# =========================================================================
# Automation Arming Endpoints
# =========================================================================


@router.get("/arm", response_model=AutomationArmStatus)
async def get_arm_status(
    state_machine=Depends(get_state_machine),
) -> AutomationArmStatus:
    """
    Get current automation arming status.

    Returns whether automation is armed and GenSlave connection status.
    """
    status = await state_machine.get_arm_status()
    return AutomationArmStatus(**status)


@router.post("/arm", response_model=ArmResponse)
async def arm_automation(
    request: ArmRequest = ArmRequest(),
    state_machine=Depends(get_state_machine),
) -> ArmResponse:
    """
    Arm the automation system.

    Arming enables all automated actions:
    - Victron signal will trigger generator start/stop
    - Scheduled runs will execute
    - Heartbeat failures will trigger safety actions

    Before arming, the system verifies GenSlave connectivity.
    Warnings are returned if connectivity is degraded.
    """
    result = await state_machine.arm_automation(source=request.source)
    return ArmResponse(**result)


@router.post("/disarm", response_model=ArmResponse)
async def disarm_automation(
    request: ArmRequest = ArmRequest(),
    state_machine=Depends(get_state_machine),
) -> ArmResponse:
    """
    Disarm the automation system.

    Disarming blocks all automated actions:
    - Victron signals are logged but not acted upon
    - Scheduled runs are skipped
    - No automatic start/stop of generator

    WARNING: If the generator is running when disarmed, it will NOT
    be stopped automatically. Use manual stop if needed.
    """
    result = await state_machine.disarm_automation(source=request.source)
    return ArmResponse(**result)
