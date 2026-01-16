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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.dependencies import get_db
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
        scheduled_start=schedule.scheduled_start,
        duration_minutes=schedule.duration_minutes,
        recurring=schedule.recurring,
        recurrence_pattern=schedule.recurrence_pattern,
        recurrence_end_date=schedule.recurrence_end_date,
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
    enabled_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> List[ScheduleResponse]:
    """
    List all scheduled runs.

    Use enabled_only=true to filter to only enabled schedules.
    """
    query = select(ScheduledRun).order_by(ScheduledRun.scheduled_start)

    if enabled_only:
        query = query.where(ScheduledRun.enabled == True)

    result = await db.execute(query)
    schedules = result.scalars().all()

    return [_schedule_to_response(s) for s in schedules]


@router.post("", response_model=ScheduleResponse)
@router.post("/", response_model=ScheduleResponse)
async def create_schedule(
    request: ScheduleCreateRequest,
    db: AsyncSession = Depends(get_db),
    scheduler_service=Depends(get_scheduler_service),
) -> ScheduleResponse:
    """
    Create a new scheduled generator run.
    """
    schedule = ScheduledRun(
        name=request.name,
        scheduled_start=request.scheduled_start,
        duration_minutes=request.duration_minutes,
        recurring=request.recurring,
        recurrence_pattern=request.recurrence_pattern,
        recurrence_end_date=request.recurrence_end_date,
        enabled=request.enabled,
        next_execution=request.scheduled_start if request.enabled else None,
    )

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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
        setattr(schedule, field, value)

    # Update next_execution if schedule changed
    if "scheduled_start" in update_data or "enabled" in update_data:
        schedule.next_execution = (
            schedule.scheduled_start if schedule.enabled else None
        )

    await db.commit()
    await db.refresh(schedule)

    # Update scheduler
    await scheduler_service.update_schedule(schedule)

    return _schedule_to_response(schedule)


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
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
