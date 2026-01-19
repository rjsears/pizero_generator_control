# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/models/generator_info.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 19th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Generator info model - singleton table for generator specifications and fuel consumption."""

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GeneratorInfo(Base):
    """
    Stores generator specifications and fuel consumption rates.

    Always exactly one row with id=1 (singleton pattern).
    """

    __tablename__ = "generator_info"
    __table_args__ = (
        CheckConstraint("id = 1", name="chk_generator_info_single_row"),
        CheckConstraint(
            "fuel_type IS NULL OR fuel_type IN ('lpg', 'natural_gas', 'diesel')",
            name="chk_fuel_type",
        ),
        CheckConstraint(
            "load_expected IS NULL OR load_expected IN (50, 100)",
            name="chk_load_expected",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, default=1)

    # Generator identification
    manufacturer: Mapped[Optional[str]] = mapped_column(nullable=True)
    model_number: Mapped[Optional[str]] = mapped_column(nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Fuel configuration
    fuel_type: Mapped[Optional[str]] = mapped_column(nullable=True)  # 'lpg', 'natural_gas', 'diesel'
    load_expected: Mapped[Optional[int]] = mapped_column(nullable=True)  # 50 or 100

    # Fuel consumption rates (gallons per hour)
    fuel_consumption_50: Mapped[Optional[float]] = mapped_column(nullable=True)  # gal/hr at 50% load
    fuel_consumption_100: Mapped[Optional[float]] = mapped_column(nullable=True)  # gal/hr at 100% load

    # Metadata
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    @classmethod
    async def get_instance(cls, db: AsyncSession) -> "GeneratorInfo":
        """Get or create the singleton generator info row."""
        result = await db.execute(select(cls).where(cls.id == 1))
        info = result.scalar_one_or_none()
        if not info:
            info = cls(id=1)
            db.add(info)
            await db.commit()
            await db.refresh(info)
        return info

    def get_consumption_rate(self) -> Optional[float]:
        """Get the fuel consumption rate based on current load setting."""
        if self.load_expected == 50:
            return self.fuel_consumption_50
        elif self.load_expected == 100:
            return self.fuel_consumption_100
        return None
