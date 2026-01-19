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
    trigger: Literal["idle", "victron", "manual", "scheduled"] = Field(
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
    trigger_type: Literal["victron", "manual", "scheduled"]
    end_reason: Optional[
        Literal["victron", "manual", "scheduled_end", "comm_loss", "override", "error"]
    ] = Field(None, description="Why the run ended")
    scheduled_run_id: Optional[int] = None
    notes: Optional[str] = None

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
