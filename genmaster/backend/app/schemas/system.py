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


class HOAStatus(BaseModel):
    """HOA (Quiet/Auto/Run) selector status."""

    state: Literal["quiet", "auto", "run", "fault"] = Field(
        description=(
            "Current operational HOA position. Returns 'auto' during the "
            "post-boot grace window regardless of physical switch position."
        )
    )
    raw_state: Literal["quiet", "auto", "run", "fault"] = Field(
        description=(
            "Decoded switch state IGNORING the boot delay — for diagnostics. "
            "Differs from `state` only while boot_delay_active is true."
        )
    )
    hoa_monitor_running: bool = Field(
        description=(
            "Whether the HOA monitor's polling loop is active. NOT related "
            "to whether the generator is running — that lives on the "
            "generator status object."
        )
    )
    enabled: bool = Field(
        description="Whether the monitor is enabled via HOA_SWITCH_ENABLED"
    )
    mock_mode: bool = Field(description="Whether running in mock GPIO mode")
    boot_delay_active: bool = Field(
        description="True if we're inside the post-boot grace window"
    )
    boot_delay_seconds: int = Field(
        description="Configured boot delay window length, in seconds"
    )
    boot_complete_at: Optional[int] = Field(
        None,
        description="Unix timestamp at which the boot delay window expires",
    )
    raw_quiet_pressed: bool = Field(
        description="Raw GPIO22 read (Quiet contact closed to GND)"
    )
    raw_run_pressed: bool = Field(
        description="Raw GPIO27 read (Run contact closed to GND)"
    )
    gpio_quiet: int = Field(description="GPIO pin number for the Quiet contact")
    gpio_run: int = Field(description="GPIO pin number for the Run contact")
    state_change_count: int = Field(
        description="Number of state transitions since service start"
    )
    last_state_change_at: Optional[int] = Field(
        None, description="Unix timestamp of the most recent state change"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "state": "auto",
                "raw_state": "auto",
                "hoa_monitor_running": True,
                "enabled": True,
                "mock_mode": False,
                "boot_delay_active": False,
                "boot_delay_seconds": 90,
                "boot_complete_at": 1715630090,
                "raw_quiet_pressed": False,
                "raw_run_pressed": False,
                "gpio_quiet": 22,
                "gpio_run": 27,
                "state_change_count": 0,
                "last_state_change_at": None,
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
    hoa: HOAStatus = Field(description="HOA (Quiet/Auto/Run) selector status")
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
