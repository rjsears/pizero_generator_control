# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/schemas/override.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Override-related Pydantic schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class OverrideStatus(BaseModel):
    """Current override status."""

    enabled: bool = Field(description="Whether override is currently active")
    override_type: Literal["none", "force_run", "force_stop"] = Field(
        description="Type of override: none, force_run, or force_stop"
    )

    class Config:
        json_schema_extra = {"example": {"enabled": False, "override_type": "none"}}


class OverrideEnableRequest(BaseModel):
    """Request to enable manual override."""

    override_type: Literal["force_run", "force_stop"] = Field(
        description="Type of override to enable"
    )

    class Config:
        json_schema_extra = {"example": {"override_type": "force_run"}}


class OverrideDisableResponse(BaseModel):
    """Response after disabling override."""

    success: bool
    message: str
    previous_type: str = Field(description="The override type that was disabled")
