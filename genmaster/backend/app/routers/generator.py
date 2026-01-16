# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/generator.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Generator control API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.dependencies import DbSession, get_db
from app.models import GeneratorRun
from app.schemas import (
    GeneratorRunHistory,
    GeneratorStartRequest,
    GeneratorStartResponse,
    GeneratorStats,
    GeneratorStatus,
    GeneratorStopRequest,
    GeneratorStopResponse,
)

router = APIRouter()


def get_state_machine():
    """Get state machine from app state."""
    from app.main import state_machine

    return state_machine


def get_scheduler_service():
    """Get scheduler service from app state."""
    from app.main import scheduler_service

    return scheduler_service


@router.get("/state", response_model=GeneratorStatus)
async def get_generator_state(
    state_machine=Depends(get_state_machine),
) -> GeneratorStatus:
    """
    Get current generator status.

    Returns whether generator is running, how long, and what triggered it.
    """
    return await state_machine.get_generator_status()


@router.post("/start", response_model=GeneratorStartResponse)
async def start_generator(
    request: GeneratorStartRequest,
    state_machine=Depends(get_state_machine),
    scheduler_service=Depends(get_scheduler_service),
) -> GeneratorStartResponse:
    """
    Start the generator manually.

    Optionally specify a duration for auto-stop.
    """
    try:
        run = await state_machine.start_generator(
            trigger="manual",
            notes=request.notes,
        )

        # Schedule auto-stop if duration specified
        if request.duration_minutes:
            await scheduler_service.schedule_auto_stop(
                run.id, request.duration_minutes
            )

        return GeneratorStartResponse(
            success=True,
            message="Generator started successfully",
            run_id=run.id,
            start_time=run.start_time,
        )

    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/stop", response_model=GeneratorStopResponse)
async def stop_generator(
    request: Optional[GeneratorStopRequest] = None,
    state_machine=Depends(get_state_machine),
    scheduler_service=Depends(get_scheduler_service),
) -> GeneratorStopResponse:
    """
    Stop the generator manually.
    """
    # Get current status to get run_id
    status = await state_machine.get_generator_status()

    if not status.running:
        raise HTTPException(status_code=409, detail="Generator is not running")

    run_id = status.current_run_id

    # Cancel any scheduled auto-stop
    if run_id:
        scheduler_service.cancel_auto_stop(run_id)

    # Stop generator
    run = await state_machine.stop_generator(
        reason="manual",
        notes=request.reason if request else None,
    )

    return GeneratorStopResponse(
        success=True,
        message="Generator stopped successfully",
        run_id=run.id if run else run_id,
        duration_seconds=run.duration_seconds if run else 0,
    )


@router.get("/history", response_model=List[GeneratorRunHistory])
async def get_generator_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    trigger_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> List[GeneratorRunHistory]:
    """
    Get generator run history.

    Supports pagination and filtering by trigger type.
    """
    query = select(GeneratorRun).order_by(GeneratorRun.start_time.desc())

    if trigger_type:
        query = query.where(GeneratorRun.trigger_type == trigger_type)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    runs = result.scalars().all()

    return [
        GeneratorRunHistory(
            id=run.id,
            start_time=run.start_time,
            stop_time=run.stop_time,
            duration_seconds=run.duration_seconds,
            trigger_type=run.trigger_type,
            stop_reason=run.stop_reason,
            scheduled_run_id=run.scheduled_run_id,
            notes=run.notes,
            created_at=run.created_at.isoformat(),
        )
        for run in runs
    ]


@router.get("/stats", response_model=GeneratorStats)
async def get_generator_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> GeneratorStats:
    """
    Get generator runtime statistics.

    Returns total runs, runtime, and breakdown by trigger type.
    """
    import time

    cutoff = int(time.time()) - (days * 86400)

    # Get all runs in period
    result = await db.execute(
        select(GeneratorRun).where(GeneratorRun.start_time >= cutoff)
    )
    runs = result.scalars().all()

    # Calculate stats
    total_runs = len(runs)
    total_runtime = sum(r.duration_seconds or 0 for r in runs)

    runs_by_trigger = {"victron": 0, "manual": 0, "scheduled": 0}
    runtime_by_trigger = {"victron": 0, "manual": 0, "scheduled": 0}

    for run in runs:
        if run.trigger_type in runs_by_trigger:
            runs_by_trigger[run.trigger_type] += 1
            runtime_by_trigger[run.trigger_type] += run.duration_seconds or 0

    return GeneratorStats(
        period_days=days,
        total_runs=total_runs,
        total_runtime_seconds=total_runtime,
        total_runtime_hours=round(total_runtime / 3600, 2),
        average_runtime_seconds=round(total_runtime / total_runs, 1) if total_runs > 0 else 0,
        runs_by_trigger=runs_by_trigger,
        runtime_by_trigger=runtime_by_trigger,
    )
