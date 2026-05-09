# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/schemas/generator.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Generator-related Pydantic schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class GeneratorStatus(BaseModel):
    """Current generator status."""

    running: bool = Field(description="Whether the generator is currently running")
    start_time: Optional[int] = Field(
        None, description="Unix timestamp when generator started"
    )
    runtime_seconds: Optional[int] = Field(
        None, description="Current runtime in seconds"
    )
    trigger: Literal["idle", "victron", "manual", "scheduled", "exercise"] = Field(
        description="What triggered the current run"
    )
    current_run_id: Optional[int] = Field(None, description="ID of the current run")

    class Config:
        json_schema_extra = {
            "example": {
                "running": True,
                "start_time": 1705320000,
                "runtime_seconds": 3600,
                "trigger": "victron",
                "current_run_id": 42,
            }
        }


class GeneratorStartRequest(BaseModel):
    """Request to start the generator manually."""

    duration_minutes: Optional[int] = Field(
        None,
        ge=1,
        le=1440,
        description="Duration in minutes (1-1440). If not set, runs until manually stopped.",
    )
    notes: Optional[str] = Field(
        None, max_length=500, description="Optional notes for this run"
    )

    class Config:
        json_schema_extra = {
            "example": {"duration_minutes": 30, "notes": "Monthly exercise run"}
        }


class GeneratorStartResponse(BaseModel):
    """Response after starting the generator."""

    success: bool
    message: str
    run_id: int = Field(description="ID of the new generator run")
    start_time: int = Field(description="Unix timestamp when generator started")


class GeneratorStopRequest(BaseModel):
    """Request to stop the generator manually."""

    reason: Optional[str] = Field(
        None, max_length=200, description="Optional reason for stopping"
    )


class GeneratorStopResponse(BaseModel):
    """Response after stopping the generator."""

    success: bool
    message: str
    run_id: int = Field(description="ID of the stopped generator run")
    duration_seconds: int = Field(description="Total runtime in seconds")


class GeneratorRunHistory(BaseModel):
    """Historical generator run record."""

    id: int
    started_at: int = Field(description="Unix timestamp when run started")
    ended_at: Optional[int] = Field(None, description="Unix timestamp when run ended")
    duration_minutes: Optional[float] = Field(None, description="Duration in minutes")
    trigger_type: Literal["victron", "manual", "scheduled", "exercise"]
    end_reason: Optional[
        Literal["victron", "manual", "scheduled_end", "exercise_end", "comm_loss", "override", "error", "max_runtime"]
    ] = Field(None, description="Why the run ended")
    scheduled_run_id: Optional[int] = None
    notes: Optional[str] = None
    # Fuel tracking fields
    fuel_type_at_run: Optional[str] = Field(None, description="Fuel type used during this run")
    load_at_run: Optional[int] = Field(None, description="Load setting during this run (50 or 100)")
    fuel_consumption_rate: Optional[float] = Field(None, description="Fuel consumption rate (gal/hr)")
    estimated_fuel_used: Optional[float] = Field(None, description="Estimated fuel consumed (gallons)")

    class Config:
        from_attributes = True


class GeneratorHistoryResponse(BaseModel):
    """Paginated generator run history response."""

    runs: list[GeneratorRunHistory] = Field(description="List of generator runs")
    total: int = Field(description="Total number of runs matching filters")


class GeneratorStats(BaseModel):
    """Generator runtime statistics."""

    period_days: int = Field(description="Statistics period in days")
    total_runs: int = Field(description="Total number of runs")
    total_runtime_seconds: int = Field(description="Total runtime in seconds")
    total_runtime_hours: float = Field(description="Total runtime in hours")
    average_runtime_seconds: float = Field(description="Average runtime per run")
    runs_by_trigger: dict[str, int] = Field(
        description="Run counts by trigger type (victron, manual, scheduled)"
    )
    runtime_by_trigger: dict[str, int] = Field(
        description="Runtime in seconds by trigger type"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "period_days": 30,
                "total_runs": 15,
                "total_runtime_seconds": 54000,
                "total_runtime_hours": 15.0,
                "average_runtime_seconds": 3600,
                "runs_by_trigger": {"victron": 10, "manual": 3, "scheduled": 2},
                "runtime_by_trigger": {"victron": 36000, "manual": 10800, "scheduled": 7200},
            }
        }


class RuntimeLimitsStatus(BaseModel):
    """Current runtime limits status including lockout/cooldown state."""

    # Feature configuration
    enabled: bool = Field(description="Whether runtime limits feature is enabled")
    min_run_minutes: int = Field(description="Minimum run time in minutes")
    max_run_minutes: int = Field(description="Maximum run time in minutes")
    max_runtime_action: str = Field(description="Action when max runtime reached")
    cooldown_duration_minutes: int = Field(description="Cooldown period duration in minutes")

    # Lockout state
    lockout_active: bool = Field(description="Whether runtime lockout is active")
    lockout_started: Optional[int] = Field(None, description="Unix timestamp when lockout started")
    lockout_reason: Optional[str] = Field(None, description="Reason for lockout")

    # Cooldown state
    cooldown_active: bool = Field(description="Whether cooldown is active")
    cooldown_end_time: Optional[int] = Field(None, description="Unix timestamp when cooldown ends")
    cooldown_remaining_seconds: Optional[int] = Field(
        None, description="Seconds remaining in cooldown"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "min_run_minutes": 5,
                "max_run_minutes": 480,
                "max_runtime_action": "cooldown",
                "cooldown_duration_minutes": 60,
                "lockout_active": False,
                "lockout_started": None,
                "lockout_reason": None,
                "cooldown_active": True,
                "cooldown_end_time": 1705330000,
                "cooldown_remaining_seconds": 1800,
            }
        }


class LockoutClearRequest(BaseModel):
    """Request to clear runtime lockout."""

    acknowledge: bool = Field(
        description="Acknowledge that you understand the generator reached max runtime"
    )


class LockoutClearResponse(BaseModel):
    """Response after clearing runtime lockout."""

    success: bool
    message: str


class FuelUsageResponse(BaseModel):
    """Fuel usage tracking response."""

    total_fuel_used: float = Field(description="Total fuel used in gallons since reset")
    reset_timestamp: Optional[int] = Field(
        None, description="Unix timestamp when fuel tracking was last reset"
    )
    runs_counted: int = Field(description="Number of runs included in the total")


class FuelResetResponse(BaseModel):
    """Response after resetting fuel tracking."""

    success: bool
    message: str
    reset_timestamp: int = Field(description="Unix timestamp of the reset")
