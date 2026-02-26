# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/schemas/system.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""System information Pydantic schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.generator import GeneratorStatus
from app.schemas.health import SlaveHealth
from app.schemas.override import OverrideStatus


class SystemHealth(BaseModel):
    """System health metrics for a single device."""

    hostname: str = Field(description="System hostname")
    platform: str = Field(description="Platform identifier (e.g., 'linux')")
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
        description="Overall health status based on thresholds"
    )
    warnings: list[str] = Field(
        default_factory=list, description="List of warning messages"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "hostname": "genmaster",
                "platform": "linux",
                "cpu_percent": 15.5,
                "ram_total_mb": 8192,
                "ram_used_mb": 2048,
                "ram_percent": 25.0,
                "disk_total_gb": 500.0,
                "disk_used_gb": 125.0,
                "disk_percent": 25.0,
                "temperature_celsius": 45.2,
                "uptime_seconds": 86400,
                "status": "healthy",
                "warnings": [],
            }
        }


class VictronStatus(BaseModel):
    """Victron relay input status."""

    signal_state: bool = Field(
        description="Current state of GPIO17 (True = generator wanted)"
    )
    last_change: Optional[int] = Field(
        None, description="Unix timestamp of last state change"
    )
    gpio_pin: int = Field(description="GPIO pin number being monitored")
    mock_mode: bool = Field(description="Whether running in mock GPIO mode")

    class Config:
        json_schema_extra = {
            "example": {
                "signal_state": False,
                "last_change": 1705320000,
                "gpio_pin": 17,
                "mock_mode": False,
            }
        }


class CombinedSystemHealth(BaseModel):
    """Combined health for GenMaster and GenSlave."""

    genmaster: SystemHealth = Field(description="GenMaster system health")
    genslave: Optional[SystemHealth] = Field(
        None, description="GenSlave system health (if connected)"
    )
    overall_status: Literal["healthy", "warning", "critical"] = Field(
        description="Overall system status"
    )


class FullSystemStatus(BaseModel):
    """Complete system status combining all components."""

    generator: GeneratorStatus = Field(description="Generator status")
    victron: VictronStatus = Field(description="Victron relay input status")
    slave_health: SlaveHealth = Field(description="GenSlave connection health")
    override: OverrideStatus = Field(description="Manual override status")
    system_health: SystemHealth = Field(description="GenMaster system health")
    relay_armed: bool = Field(description="Whether GenSlave relay is armed")
    timestamp: int = Field(description="Unix timestamp of this status")


class AutomationArmStatus(BaseModel):
    """Relay arming status."""

    armed: bool = Field(description="Whether relay is armed")
    slave_connection: str = Field(
        description="GenSlave connection status ('connected', 'disconnected', 'unknown')"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "armed": True,
                "slave_connection": "connected",
            }
        }


class ArmRequest(BaseModel):
    """Request to arm the automation system."""

    source: str = Field(
        default="api",
        description="What initiated the arm request (e.g., 'api', 'ui', 'startup')",
    )


class ArmResponse(BaseModel):
    """Response from arm/disarm operations."""

    success: bool = Field(description="Whether the operation succeeded")
    armed: bool = Field(description="Current armed state")
    message: str = Field(description="Human-readable status message")
    armed_at: Optional[int] = Field(None, description="Unix timestamp when armed")
    warnings: list[str] = Field(
        default_factory=list, description="Any warnings during the operation"
    )


class WifiWatchdogStatus(BaseModel):
    """WiFi watchdog service status."""

    installed: bool = Field(description="Whether watchdog script is installed on host")
    enabled: bool = Field(description="Whether systemd service is enabled")
    running: bool = Field(description="Whether service is currently active")
    failure_count: int = Field(default=0, description="Consecutive connectivity failures")
    last_recovery: Optional[str] = Field(
        default=None, description="Timestamp of last recovery"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "installed": True,
                "enabled": True,
                "running": True,
                "failure_count": 0,
                "last_recovery": None,
            }
        }


class WifiWatchdogActionResponse(BaseModel):
    """Response from WiFi watchdog actions (install/enable/disable)."""

    success: bool = Field(description="Whether the action succeeded")
    message: str = Field(description="Human-readable status message")
    status: Optional[WifiWatchdogStatus] = Field(
        default=None, description="Current watchdog status after action"
    )
