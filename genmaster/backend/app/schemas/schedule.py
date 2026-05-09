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

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ScheduleCreateRequest(BaseModel):
    """Request to create a new scheduled generator run.

    Supports weekly schedule format with days_of_week and start_time.
    """

    name: Optional[str] = Field(
        None, max_length=100, description="Optional name for this schedule"
    )
    start_time: str = Field(
        description="Time of day to start (HH:MM format, e.g., '09:00')"
    )
    duration_minutes: int = Field(
        ge=1, le=1440, description="Duration in minutes (1-1440)"
    )
    days_of_week: List[int] = Field(
        description="Days to run (0=Sunday, 1=Monday, ..., 6=Saturday)"
    )
    enabled: bool = Field(default=True, description="Whether this schedule is active")

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: str) -> str:
        """Validate start_time is in HH:MM format."""
        try:
            parts = v.split(":")
            if len(parts) != 2:
                raise ValueError()
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError()
        except (ValueError, IndexError):
            raise ValueError("start_time must be in HH:MM format (e.g., '09:00')")
        return v

    @field_validator("days_of_week")
    @classmethod
    def validate_days_of_week(cls, v: List[int]) -> List[int]:
        """Validate days_of_week contains valid day numbers."""
        if not v:
            raise ValueError("At least one day must be selected")
        for day in v:
            if not (0 <= day <= 6):
                raise ValueError("Days must be 0-6 (Sunday=0, Saturday=6)")
        return sorted(set(v))  # Remove duplicates and sort

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Weekly Exercise",
                "start_time": "09:00",
                "duration_minutes": 30,
                "days_of_week": [1, 3, 5],
                "enabled": True,
            }
        }


class ScheduleResponse(BaseModel):
    """Response containing schedule details."""

    id: int
    name: Optional[str]
    start_time: str
    duration_minutes: int
    days_of_week: List[int]
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
    start_time: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=1440)
    days_of_week: Optional[List[int]] = None
    enabled: Optional[bool] = None

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: Optional[str]) -> Optional[str]:
        """Validate start_time is in HH:MM format."""
        if v is None:
            return v
        try:
            parts = v.split(":")
            if len(parts) != 2:
                raise ValueError()
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError()
        except (ValueError, IndexError):
            raise ValueError("start_time must be in HH:MM format (e.g., '09:00')")
        return v

    @field_validator("days_of_week")
    @classmethod
    def validate_days_of_week(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        """Validate days_of_week contains valid day numbers."""
        if v is None:
            return v
        if not v:
            raise ValueError("At least one day must be selected")
        for day in v:
            if not (0 <= day <= 6):
                raise ValueError("Days must be 0-6 (Sunday=0, Saturday=6)")
        return sorted(set(v))
