# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/models/settings.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Settings model - flexible key-value settings storage."""

from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Settings(Base):
    """Flexible key-value settings storage for UI configuration."""

    __tablename__ = "settings"
    __table_args__ = (Index("idx_settings_key", "key", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Key-Value Data
    key: Mapped[str] = mapped_column(unique=True, nullable=False)
    value: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    @classmethod
    async def get(cls, db: AsyncSession, key: str) -> Optional["Settings"]:
        """Get setting by key."""
        result = await db.execute(select(cls).where(cls.key == key))
        return result.scalar_one_or_none()

    @classmethod
    async def get_value(
        cls, db: AsyncSession, key: str, default: Any = None
    ) -> Any:
        """Get setting value by key, returning default if not found."""
        setting = await cls.get(db, key)
        return setting.value if setting else default

    @classmethod
    async def set(
        cls,
        db: AsyncSession,
        key: str,
        value: Any,
        description: Optional[str] = None,
    ) -> "Settings":
        """Set or update a setting."""
        setting = await cls.get(db, key)
        if setting:
            setting.value = value
            if description is not None:
                setting.description = description
        else:
            setting = cls(key=key, value=value, description=description)
            db.add(setting)
        await db.commit()
        await db.refresh(setting)
        return setting

    @classmethod
    async def get_all(cls, db: AsyncSession) -> List["Settings"]:
        """Get all settings."""
        result = await db.execute(select(cls))
        return list(result.scalars().all())
