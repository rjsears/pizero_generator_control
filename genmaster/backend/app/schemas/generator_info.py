# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/schemas/generator_info.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 19th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Generator info Pydantic schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FuelTypeEnum(str, Enum):
    """Fuel type options."""

    lpg = "lpg"
    natural_gas = "natural_gas"
    diesel = "diesel"


class LoadExpectedEnum(int, Enum):
    """Load expected options."""

    fifty = 50
    hundred = 100


class GeneratorInfoBase(BaseModel):
    """Base schema with shared generator info fields."""

    manufacturer: Optional[str] = Field(None, max_length=100, description="Generator manufacturer")
    model_number: Optional[str] = Field(None, max_length=100, description="Model number")
    serial_number: Optional[str] = Field(None, max_length=100, description="Serial number")
    fuel_type: Optional[FuelTypeEnum] = Field(None, description="Fuel type (lpg, natural_gas, diesel)")
    load_expected: Optional[LoadExpectedEnum] = Field(None, description="Expected load setting (50 or 100)")
    fuel_consumption_50: Optional[float] = Field(
        None, ge=0, le=100, description="Fuel consumption at 50% load (gal/hr)"
    )
    fuel_consumption_100: Optional[float] = Field(
        None, ge=0, le=100, description="Fuel consumption at 100% load (gal/hr)"
    )


class GeneratorInfoResponse(GeneratorInfoBase):
    """Response schema for GET /generator-info."""

    updated_at: datetime = Field(description="Last update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "manufacturer": "Generac",
                "model_number": "7043",
                "serial_number": "ABC123456",
                "fuel_type": "lpg",
                "load_expected": 50,
                "fuel_consumption_50": 1.6,
                "fuel_consumption_100": 2.8,
                "updated_at": "2026-01-19T10:30:00",
            }
        }


class GeneratorInfoUpdate(BaseModel):
    """Request schema for PATCH /generator-info - all fields optional for partial updates."""

    manufacturer: Optional[str] = Field(None, max_length=100, description="Generator manufacturer")
    model_number: Optional[str] = Field(None, max_length=100, description="Model number")
    serial_number: Optional[str] = Field(None, max_length=100, description="Serial number")
    fuel_type: Optional[FuelTypeEnum] = Field(None, description="Fuel type (lpg, natural_gas, diesel)")
    load_expected: Optional[LoadExpectedEnum] = Field(None, description="Expected load setting (50 or 100)")
    fuel_consumption_50: Optional[float] = Field(
        None, ge=0, le=100, description="Fuel consumption at 50% load (gal/hr)"
    )
    fuel_consumption_100: Optional[float] = Field(
        None, ge=0, le=100, description="Fuel consumption at 100% load (gal/hr)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "fuel_type": "lpg",
                "load_expected": 50,
                "fuel_consumption_50": 1.6,
            }
        }
