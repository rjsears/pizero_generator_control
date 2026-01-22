# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/schedule.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Schedule management API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.future import select

from app.dependencies import DbSession
from app.models import ScheduledRun
from app.schemas import (
    ScheduleCreateRequest,
    ScheduleResponse,
    ScheduleUpdateRequest,
)

router = APIRouter()


def get_scheduler_service():
    """Get scheduler service from app state."""
    from app.main import scheduler_service

    return scheduler_service


def _schedule_to_response(schedule: ScheduledRun) -> ScheduleResponse:
    """Convert ScheduledRun model to response schema."""
    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        start_time=schedule.start_time,
        duration_minutes=schedule.duration_minutes,
        days_of_week=schedule.days_of_week,
        enabled=schedule.enabled,
        last_executed=schedule.last_executed,
        next_execution=schedule.next_execution,
        execution_count=schedule.execution_count,
        created_at=schedule.created_at.isoformat(),
        updated_at=schedule.updated_at.isoformat(),
    )


@router.get("", response_model=List[ScheduleResponse])
@router.get("/", response_model=List[ScheduleResponse])
async def list_schedules(
    db: DbSession,
    enabled_only: bool = Query(False),
) -> List[ScheduleResponse]:
    """
    List all scheduled runs.

    Use enabled_only=true to filter to only enabled schedules.
    """
    query = select(ScheduledRun).order_by(ScheduledRun.start_time)

    if enabled_only:
        query = query.where(ScheduledRun.enabled == True)

    result = await db.execute(query)
    schedules = result.scalars().all()

    return [_schedule_to_response(s) for s in schedules]


@router.post("", response_model=ScheduleResponse)
@router.post("/", response_model=ScheduleResponse)
async def create_schedule(
    request: ScheduleCreateRequest,
    db: DbSession,
    scheduler_service=Depends(get_scheduler_service),
) -> ScheduleResponse:
    """
    Create a new scheduled generator run.
    """
    schedule = ScheduledRun(
        name=request.name,
        start_time=request.start_time,
        duration_minutes=request.duration_minutes,
        enabled=request.enabled,
    )
    # Set days_of_week via property (handles JSON serialization)
    schedule.days_of_week = request.days_of_week

    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    # Add to scheduler if enabled
    if schedule.enabled:
        await scheduler_service.add_schedule(schedule)

    return _schedule_to_response(schedule)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    db: DbSession,
) -> ScheduleResponse:
    """
    Get a specific scheduled run.
    """
    result = await db.execute(
        select(ScheduledRun).where(ScheduledRun.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return _schedule_to_response(schedule)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    request: ScheduleUpdateRequest,
    db: DbSession,
    scheduler_service=Depends(get_scheduler_service),
) -> ScheduleResponse:
    """
    Update an existing scheduled run.
    """
    result = await db.execute(
        select(ScheduledRun).where(ScheduledRun.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        # Handle days_of_week specially (uses property setter for JSON serialization)
        if field == "days_of_week":
            schedule.days_of_week = value
        else:
            setattr(schedule, field, value)

    await db.commit()
    await db.refresh(schedule)

    # Update scheduler
    await scheduler_service.update_schedule(schedule)

    return _schedule_to_response(schedule)


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: DbSession,
    scheduler_service=Depends(get_scheduler_service),
) -> dict:
    """
    Delete a scheduled run.
    """
    result = await db.execute(
        select(ScheduledRun).where(ScheduledRun.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Remove from scheduler
    scheduler_service.remove_schedule(schedule_id)

    # Delete from database
    await db.delete(schedule)
    await db.commit()

    return {"success": True, "message": f"Schedule {schedule_id} deleted"}
