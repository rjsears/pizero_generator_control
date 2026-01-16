# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/schemas/schedule.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Schedule-related Pydantic schemas."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ScheduleCreateRequest(BaseModel):
    """Request to create a new scheduled generator run."""

    name: Optional[str] = Field(
        None, max_length=100, description="Optional name for this schedule"
    )
    scheduled_start: int = Field(
        description="Unix timestamp for when the generator should start"
    )
    duration_minutes: int = Field(
        ge=1, le=1440, description="Duration in minutes (1-1440)"
    )
    recurring: bool = Field(default=False, description="Whether this schedule repeats")
    recurrence_pattern: Optional[str] = Field(
        None,
        max_length=100,
        description="Recurrence pattern: 'daily', 'weekly', or cron expression",
    )
    recurrence_end_date: Optional[int] = Field(
        None, description="Unix timestamp when recurrence ends"
    )
    enabled: bool = Field(default=True, description="Whether this schedule is active")

    @field_validator("recurrence_pattern")
    @classmethod
    def validate_recurrence_pattern(cls, v: Optional[str], info) -> Optional[str]:
        """Validate recurrence pattern if recurring is True."""
        # Access other field values through info.data
        if info.data.get("recurring") and not v:
            raise ValueError("recurrence_pattern required when recurring is True")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Weekly Exercise",
                "scheduled_start": 1705320000,
                "duration_minutes": 30,
                "recurring": True,
                "recurrence_pattern": "weekly",
                "enabled": True,
            }
        }


class ScheduleResponse(BaseModel):
    """Response containing schedule details."""

    id: int
    name: Optional[str]
    scheduled_start: int
    duration_minutes: int
    recurring: bool
    recurrence_pattern: Optional[str]
    recurrence_end_date: Optional[int]
    enabled: bool
    last_executed: Optional[int]
    next_execution: Optional[int]
    execution_count: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ScheduleUpdateRequest(BaseModel):
    """Request to update an existing schedule."""

    name: Optional[str] = Field(None, max_length=100)
    scheduled_start: Optional[int] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=1440)
    recurring: Optional[bool] = None
    recurrence_pattern: Optional[str] = Field(None, max_length=100)
    recurrence_end_date: Optional[int] = None
    enabled: Optional[bool] = None
