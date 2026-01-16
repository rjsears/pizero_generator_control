# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genslave/app/routers/system.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 16th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""System information API endpoints."""

import logging
import os
import platform
from typing import Literal, Optional

import psutil
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])


# =========================================================================
# Schemas
# =========================================================================


class SystemInfo(BaseModel):
    """System information and resource usage."""

    hostname: str = Field(description="System hostname")
    platform: str = Field(description="Platform identifier")
    cpu_percent: float = Field(description="CPU usage percentage")
    ram_total_mb: int = Field(description="Total RAM in MB")
    ram_used_mb: int = Field(description="Used RAM in MB")
    ram_percent: float = Field(description="RAM usage percentage")
    disk_total_gb: float = Field(description="Total disk space in GB")
    disk_used_gb: float = Field(description="Used disk space in GB")
    disk_percent: float = Field(description="Disk usage percentage")
    temperature_celsius: Optional[float] = Field(
        None, description="CPU temperature in Celsius"
    )
    uptime_seconds: int = Field(description="System uptime in seconds")
    status: Literal["healthy", "warning", "critical"] = Field(
        description="Overall health status"
    )
    warnings: list[str] = Field(
        default_factory=list, description="List of warning messages"
    )


class ConfigUpdate(BaseModel):
    """Configuration update from GenMaster."""

    failsafe_timeout_seconds: Optional[int] = Field(
        None, description="New failsafe timeout"
    )
    webhook_url: Optional[str] = Field(None, description="Backup webhook URL")
    webhook_secret: Optional[str] = Field(None, description="Webhook secret")


class ConfigResponse(BaseModel):
    """Response from config update."""

    success: bool = Field(description="Whether update was successful")
    message: str = Field(description="Status message")


# =========================================================================
# Endpoints
# =========================================================================


@router.get("", response_model=SystemInfo)
async def get_system_info() -> SystemInfo:
    """
    Get system information and resource usage.

    Returns CPU, RAM, disk, temperature, and overall health status.
    """
    warnings = []
    status = "healthy"

    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=0.1)
    if cpu_percent > 90:
        warnings.append(f"CPU usage critical: {cpu_percent}%")
        status = "critical"
    elif cpu_percent > 80:
        warnings.append(f"CPU usage high: {cpu_percent}%")
        if status != "critical":
            status = "warning"

    # Memory usage
    memory = psutil.virtual_memory()
    ram_percent = memory.percent
    if ram_percent > 90:
        warnings.append(f"Memory usage critical: {ram_percent}%")
        status = "critical"
    elif ram_percent > 80:
        warnings.append(f"Memory usage high: {ram_percent}%")
        if status != "critical":
            status = "warning"

    # Disk usage
    disk = psutil.disk_usage("/")
    disk_percent = disk.percent
    if disk_percent > 95:
        warnings.append(f"Disk usage critical: {disk_percent}%")
        status = "critical"
    elif disk_percent > 85:
        warnings.append(f"Disk usage high: {disk_percent}%")
        if status != "critical":
            status = "warning"

    # Temperature
    temperature = _get_cpu_temperature()
    if temperature:
        if temperature > 80:
            warnings.append(f"Temperature critical: {temperature}°C")
            status = "critical"
        elif temperature > 70:
            warnings.append(f"Temperature high: {temperature}°C")
            if status != "critical":
                status = "warning"

    return SystemInfo(
        hostname=platform.node(),
        platform=platform.system().lower(),
        cpu_percent=cpu_percent,
        ram_total_mb=int(memory.total / (1024 * 1024)),
        ram_used_mb=int(memory.used / (1024 * 1024)),
        ram_percent=ram_percent,
        disk_total_gb=round(disk.total / (1024**3), 1),
        disk_used_gb=round(disk.used / (1024**3), 1),
        disk_percent=disk_percent,
        temperature_celsius=temperature,
        uptime_seconds=_get_uptime(),
        status=status,
        warnings=warnings,
    )


@router.post("/config", response_model=ConfigResponse)
async def update_config(config: ConfigUpdate) -> ConfigResponse:
    """
    Receive configuration push from GenMaster.

    Allows GenMaster to update certain settings on GenSlave.
    Note: Changes are applied in memory only, not persisted.
    """
    changes = []

    if config.failsafe_timeout_seconds is not None:
        # Update in memory (would need to restart for full effect)
        settings.FAILSAFE_TIMEOUT_SECONDS = config.failsafe_timeout_seconds
        changes.append(f"failsafe_timeout={config.failsafe_timeout_seconds}")

    if config.webhook_url is not None:
        settings.WEBHOOK_URL = config.webhook_url
        changes.append("webhook_url updated")

    if config.webhook_secret is not None:
        settings.WEBHOOK_SECRET = config.webhook_secret
        changes.append("webhook_secret updated")

    if changes:
        logger.info(f"Config updated: {', '.join(changes)}")
        return ConfigResponse(
            success=True,
            message=f"Updated: {', '.join(changes)}",
        )
    else:
        return ConfigResponse(
            success=True,
            message="No changes to apply",
        )


def _get_cpu_temperature() -> Optional[float]:
    """Get CPU temperature on Raspberry Pi."""
    # Try vcgencmd first (Raspberry Pi specific)
    try:
        temp_output = os.popen("vcgencmd measure_temp 2>/dev/null").read()
        if temp_output:
            # Format: "temp=45.0'C"
            temp_str = temp_output.replace("temp=", "").replace("'C", "").strip()
            return float(temp_str)
    except Exception:
        pass

    # Try thermal zone (generic Linux)
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return float(f.read().strip()) / 1000.0
    except Exception:
        pass

    return None


def _get_uptime() -> int:
    """Get system uptime in seconds."""
    try:
        with open("/proc/uptime", "r") as f:
            return int(float(f.read().split()[0]))
    except Exception:
        return 0
