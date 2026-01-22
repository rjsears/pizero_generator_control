# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/utils/system_info.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""System information utilities using psutil."""

import logging
import platform
import socket
from typing import Literal, Optional

import psutil

from app.database import AsyncSessionLocal
from app.models import Config
from app.schemas import SystemHealth

logger = logging.getLogger(__name__)


def get_cpu_info() -> dict:
    """
    Get CPU information.

    Returns:
        Dict with cpu_percent and cpu_count
    """
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "cpu_count": psutil.cpu_count(),
    }


def get_memory_info() -> dict:
    """
    Get memory information.

    In Docker containers, psutil may not correctly report memory with cgroup limits.
    This function tries to read cgroup memory info first for accurate container metrics,
    then falls back to psutil for non-containerized environments.

    Returns:
        Dict with total_mb, used_mb, available_mb, percent
    """
    # Try cgroups v2 first (modern Docker/systemd)
    try:
        cgroup_max = "/sys/fs/cgroup/memory.max"
        cgroup_current = "/sys/fs/cgroup/memory.current"

        with open(cgroup_max, "r") as f:
            max_val = f.read().strip()

        with open(cgroup_current, "r") as f:
            current = int(f.read().strip())

        # If max is "max", there's no limit - use host memory
        if max_val != "max":
            total = int(max_val)
            used = current
            available = total - used
            percent = (used / total) * 100 if total > 0 else 0

            return {
                "total_mb": total // (1024 * 1024),
                "used_mb": used // (1024 * 1024),
                "available_mb": available // (1024 * 1024),
                "percent": round(percent, 1),
            }
    except (FileNotFoundError, PermissionError, ValueError):
        pass

    # Try cgroups v1 (older Docker)
    try:
        cgroup_limit = "/sys/fs/cgroup/memory/memory.limit_in_bytes"
        cgroup_usage = "/sys/fs/cgroup/memory/memory.usage_in_bytes"

        with open(cgroup_limit, "r") as f:
            limit = int(f.read().strip())

        with open(cgroup_usage, "r") as f:
            usage = int(f.read().strip())

        # Very large limit means no effective limit - use host memory
        # (cgroups v1 uses a large number like 9223372036854771712 for "unlimited")
        host_mem = psutil.virtual_memory().total
        if limit < host_mem * 2:  # Has an actual limit
            available = limit - usage
            percent = (usage / limit) * 100 if limit > 0 else 0

            return {
                "total_mb": limit // (1024 * 1024),
                "used_mb": usage // (1024 * 1024),
                "available_mb": available // (1024 * 1024),
                "percent": round(percent, 1),
            }
    except (FileNotFoundError, PermissionError, ValueError):
        pass

    # Fallback to psutil (non-containerized or no cgroup limits)
    mem = psutil.virtual_memory()
    return {
        "total_mb": mem.total // (1024 * 1024),
        "used_mb": mem.used // (1024 * 1024),
        "available_mb": mem.available // (1024 * 1024),
        "percent": mem.percent,
    }


def get_disk_info(path: str = "/") -> dict:
    """
    Get disk information for a path.

    Args:
        path: Filesystem path to check

    Returns:
        Dict with total_gb, used_gb, free_gb, percent
    """
    disk = psutil.disk_usage(path)
    return {
        "total_gb": disk.total / (1024 * 1024 * 1024),
        "used_gb": disk.used / (1024 * 1024 * 1024),
        "free_gb": disk.free / (1024 * 1024 * 1024),
        "percent": disk.percent,
    }


def get_temperature() -> Optional[float]:
    """
    Get CPU temperature in Celsius.

    Returns:
        Temperature in Celsius, or None if not available
    """
    try:
        # Try psutil sensors
        temps = psutil.sensors_temperatures()
        if temps:
            # Try common sensor names
            for name in ["cpu_thermal", "coretemp", "cpu-thermal"]:
                if name in temps and temps[name]:
                    return temps[name][0].current

            # Fall back to first available
            for sensors in temps.values():
                if sensors:
                    return sensors[0].current

        # Try Raspberry Pi thermal zone
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return int(f.read().strip()) / 1000.0
        except (FileNotFoundError, PermissionError):
            pass

    except Exception as e:
        logger.debug(f"Could not read temperature: {e}")

    return None


def get_uptime() -> int:
    """
    Get Docker host uptime in seconds.

    Reads the host's /proc/uptime by running a quick Docker command with
    --pid=host to access the host's process namespace.

    Returns:
        Uptime in seconds
    """
    import time

    uptime_seconds = 0

    try:
        import docker

        docker_client = docker.from_env()

        # Run a quick container with --pid=host to read host's /proc/uptime
        # This gives us the actual host uptime, not container uptime
        try:
            result = docker_client.containers.run(
                "alpine:latest",
                command=["cat", "/proc/uptime"],
                pid_mode="host",
                remove=True,
                network_disabled=True,
            )
            # /proc/uptime format: "seconds_up seconds_idle"
            uptime_str = result.decode("utf-8").strip().split()[0]
            uptime_seconds = int(float(uptime_str))
        except Exception as e:
            logger.debug(f"Could not get host uptime via Docker: {e}")

    except Exception as e:
        logger.debug(f"Docker method failed: {e}")

    # Fallback: read local /proc/uptime (will be container uptime in Docker)
    if uptime_seconds <= 0:
        try:
            with open("/proc/uptime", "r") as f:
                uptime_seconds = int(float(f.read().split()[0]))
        except Exception as e:
            logger.debug(f"Fallback /proc/uptime failed: {e}")

    # Final fallback: use psutil
    if uptime_seconds <= 0:
        uptime_seconds = int(time.time() - psutil.boot_time())

    return uptime_seconds


def get_hostname() -> str:
    """Get system hostname."""
    return socket.gethostname()


def get_platform() -> str:
    """Get platform identifier."""
    return platform.system().lower()


async def get_system_health() -> SystemHealth:
    """
    Get complete system health metrics.

    Returns:
        SystemHealth schema with all metrics
    """
    # Get basic metrics
    cpu = get_cpu_info()
    mem = get_memory_info()
    disk = get_disk_info()
    temp = get_temperature()
    uptime = get_uptime()

    # Determine status based on thresholds
    warnings = []
    status: Literal["healthy", "warning", "critical"] = "healthy"

    # Get thresholds from config
    async with AsyncSessionLocal() as db:
        config = await Config.get_instance(db)

        # Check temperature
        if temp is not None:
            if temp >= config.temp_critical_celsius:
                status = "critical"
                warnings.append(f"Temperature critical: {temp:.1f}°C")
            elif temp >= config.temp_warning_celsius:
                if status != "critical":
                    status = "warning"
                warnings.append(f"Temperature high: {temp:.1f}°C")

        # Check disk
        if disk["percent"] >= config.disk_critical_percent:
            status = "critical"
            warnings.append(f"Disk critical: {disk['percent']:.1f}%")
        elif disk["percent"] >= config.disk_warning_percent:
            if status != "critical":
                status = "warning"
            warnings.append(f"Disk usage high: {disk['percent']:.1f}%")

        # Check RAM
        if mem["percent"] >= config.ram_warning_percent:
            if status != "critical":
                status = "warning"
            warnings.append(f"RAM usage high: {mem['percent']:.1f}%")

    return SystemHealth(
        hostname=get_hostname(),
        platform=get_platform(),
        cpu_percent=cpu["cpu_percent"],
        ram_total_mb=mem["total_mb"],
        ram_used_mb=mem["used_mb"],
        ram_percent=mem["percent"],
        disk_total_gb=round(disk["total_gb"], 2),
        disk_used_gb=round(disk["used_gb"], 2),
        disk_percent=disk["percent"],
        temperature_celsius=round(temp, 1) if temp else None,
        uptime_seconds=uptime,
        status=status,
        warnings=warnings,
    )
