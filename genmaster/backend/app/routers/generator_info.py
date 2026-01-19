# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/generator_info.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 19th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Generator info API endpoints."""

from fastapi import APIRouter

from app.dependencies import AdminUser, DbSession
from app.models import GeneratorInfo
from app.schemas import GeneratorInfoResponse, GeneratorInfoUpdate

router = APIRouter()


@router.get("", response_model=GeneratorInfoResponse)
@router.get("/", response_model=GeneratorInfoResponse)
async def get_generator_info(
    db: DbSession,
) -> GeneratorInfoResponse:
    """
    Get generator information.

    Returns current generator specifications and fuel consumption settings.
    """
    info = await GeneratorInfo.get_instance(db)

    return GeneratorInfoResponse(
        manufacturer=info.manufacturer,
        model_number=info.model_number,
        serial_number=info.serial_number,
        fuel_type=info.fuel_type,
        load_expected=info.load_expected,
        fuel_consumption_50=info.fuel_consumption_50,
        fuel_consumption_100=info.fuel_consumption_100,
        updated_at=info.updated_at,
    )


@router.patch("", response_model=GeneratorInfoResponse)
@router.patch("/", response_model=GeneratorInfoResponse)
async def update_generator_info(
    request: GeneratorInfoUpdate,
    db: DbSession,
    admin: AdminUser,
) -> GeneratorInfoResponse:
    """
    Update generator information.

    Partial updates are supported - only provided fields will be updated.
    Requires admin authentication.
    """
    info = await GeneratorInfo.get_instance(db)

    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        # Convert enum values to their string/int representation
        if hasattr(value, "value"):
            value = value.value
        setattr(info, field, value)

    await db.commit()
    await db.refresh(info)

    return GeneratorInfoResponse(
        manufacturer=info.manufacturer,
        model_number=info.model_number,
        serial_number=info.serial_number,
        fuel_type=info.fuel_type,
        load_expected=info.load_expected,
        fuel_consumption_50=info.fuel_consumption_50,
        fuel_consumption_100=info.fuel_consumption_100,
        updated_at=info.updated_at,
    )
