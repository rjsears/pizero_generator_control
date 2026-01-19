# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/schemas/exercise_schedule.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 19th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Exercise schedule Pydantic schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ExerciseScheduleBase(BaseModel):
    """Base schema with shared exercise schedule fields."""

    enabled: bool = Field(default=False, description="Whether exercise scheduling is enabled")
    frequency_days: int = Field(
        default=7, ge=1, le=365, description="How often to exercise (days)"
    )
    start_time: str = Field(
        default="10:00", description="Time of day to start exercise (HH:MM)"
    )
    duration_minutes: int = Field(
        default=15, ge=1, le=480, description="Exercise duration (minutes)"
    )

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: str) -> str:
        """Validate start_time format (HH:MM)."""
        try:
            parts = v.split(":")
            if len(parts) != 2:
                raise ValueError("Invalid time format")
            hour = int(parts[0])
            minute = int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time values")
            return f"{hour:02d}:{minute:02d}"
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid time format. Use HH:MM (e.g., 10:00): {e}")


class ExerciseScheduleResponse(ExerciseScheduleBase):
    """Response schema for GET /exercise."""

    last_exercise_date: Optional[date] = Field(None, description="Date of last exercise run")
    next_exercise_date: Optional[date] = Field(None, description="Computed next exercise date")
    updated_at: datetime = Field(description="Last update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "enabled": True,
                "frequency_days": 7,
                "start_time": "10:00",
                "duration_minutes": 15,
                "last_exercise_date": "2026-01-12",
                "next_exercise_date": "2026-01-19",
                "updated_at": "2026-01-12T10:15:00",
            }
        }


class ExerciseScheduleUpdate(BaseModel):
    """Request schema for PATCH /exercise - all fields optional for partial updates."""

    enabled: Optional[bool] = Field(None, description="Whether exercise scheduling is enabled")
    frequency_days: Optional[int] = Field(
        None, ge=1, le=365, description="How often to exercise (days)"
    )
    start_time: Optional[str] = Field(
        None, description="Time of day to start exercise (HH:MM)"
    )
    duration_minutes: Optional[int] = Field(
        None, ge=1, le=480, description="Exercise duration (minutes)"
    )

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: Optional[str]) -> Optional[str]:
        """Validate start_time format (HH:MM)."""
        if v is None:
            return v
        try:
            parts = v.split(":")
            if len(parts) != 2:
                raise ValueError("Invalid time format")
            hour = int(parts[0])
            minute = int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time values")
            return f"{hour:02d}:{minute:02d}"
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid time format. Use HH:MM (e.g., 10:00): {e}")

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "frequency_days": 14,
                "duration_minutes": 20,
            }
        }


class ExerciseRunNowResponse(BaseModel):
    """Response schema for POST /exercise/run-now."""

    success: bool = Field(description="Whether the exercise run was started")
    message: str = Field(description="Status message")
    run_id: Optional[int] = Field(None, description="ID of the started generator run")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Exercise run started",
                "run_id": 42,
            }
        }
