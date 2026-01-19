# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/exercise.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 19th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Exercise schedule API endpoints."""

from fastapi import APIRouter, HTTPException

from app.dependencies import AdminUser, DbSession
from app.models import ExerciseSchedule

from app.schemas import (
    ExerciseRunNowResponse,
    ExerciseScheduleResponse,
    ExerciseScheduleUpdate,
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


@router.get("", response_model=ExerciseScheduleResponse)
@router.get("/", response_model=ExerciseScheduleResponse)
async def get_exercise_schedule(
    db: DbSession,
) -> ExerciseScheduleResponse:
    """
    Get exercise schedule configuration.

    Returns current exercise settings and tracking information.
    """
    schedule = await ExerciseSchedule.get_instance(db)

    # Calculate next exercise date if not set but enabled
    next_date = schedule.next_exercise_date
    if schedule.enabled and not next_date:
        next_date = schedule.calculate_next_exercise()

    return ExerciseScheduleResponse(
        enabled=schedule.enabled,
        frequency_days=schedule.frequency_days,
        start_time=schedule.start_time,
        duration_minutes=schedule.duration_minutes,
        last_exercise_date=schedule.last_exercise_date,
        next_exercise_date=next_date,
        updated_at=schedule.updated_at,
    )


@router.patch("", response_model=ExerciseScheduleResponse)
@router.patch("/", response_model=ExerciseScheduleResponse)
async def update_exercise_schedule(
    request: ExerciseScheduleUpdate,
    db: DbSession,
    admin: AdminUser,
) -> ExerciseScheduleResponse:
    """
    Update exercise schedule configuration.

    Partial updates are supported - only provided fields will be updated.
    Requires admin authentication.
    """
    schedule = await ExerciseSchedule.get_instance(db)

    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(schedule, field, value)

    # Recalculate next exercise date when schedule is changed
    if schedule.enabled:
        schedule.next_exercise_date = schedule.calculate_next_exercise()
    else:
        schedule.next_exercise_date = None

    await db.commit()
    await db.refresh(schedule)

    return ExerciseScheduleResponse(
        enabled=schedule.enabled,
        frequency_days=schedule.frequency_days,
        start_time=schedule.start_time,
        duration_minutes=schedule.duration_minutes,
        last_exercise_date=schedule.last_exercise_date,
        next_exercise_date=schedule.next_exercise_date,
        updated_at=schedule.updated_at,
    )


@router.post("/run-now", response_model=ExerciseRunNowResponse)
async def run_exercise_now(
    db: DbSession,
    admin: AdminUser,
) -> ExerciseRunNowResponse:
    """
    Manually trigger an exercise run.

    Starts the generator with trigger='exercise' and schedules auto-stop
    after the configured duration. Requires admin authentication.
    """
    schedule = await ExerciseSchedule.get_instance(db)
    state_machine = get_state_machine()
    scheduler_service = get_scheduler_service()

    if state_machine is None:
        raise HTTPException(status_code=503, detail="State machine not initialized")

    # Check if generator can be started
    status = await state_machine.get_generator_status()
    if status.running:
        raise HTTPException(status_code=409, detail="Generator is already running")

    # Check if relay is armed
    arm_status = await state_machine.get_arm_status()
    if not arm_status.get("armed", False):
        raise HTTPException(
            status_code=409,
            detail="Cannot start exercise - GenSlave relay is not armed",
        )

    try:
        # Start generator with exercise trigger
        run = await state_machine.start_generator(
            trigger="exercise",
            notes=f"Manual exercise run ({schedule.duration_minutes} minutes)",
        )

        # Schedule auto-stop after configured duration
        if scheduler_service:
            await scheduler_service.schedule_auto_stop(
                run.id, schedule.duration_minutes, stop_reason="exercise_end"
            )

        return ExerciseRunNowResponse(
            success=True,
            message=f"Exercise run started for {schedule.duration_minutes} minutes",
            run_id=run.id,
        )

    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
