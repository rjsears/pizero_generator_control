# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/models/session.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Session model - user authentication sessions."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, delete, func
from sqlalchemy.ext.asyncio import AsyncSession as AsyncDBSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Session(Base):
    """Stores user authentication sessions."""

    __tablename__ = "sessions"
    __table_args__ = (
        Index("idx_sessions_token", "token", unique=True),
        Index("idx_sessions_user_id", "user_id"),
        Index("idx_sessions_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Session Data
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)

    # Client Info
    user_agent: Mapped[Optional[str]] = mapped_column(nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    @property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

    @classmethod
    async def cleanup_expired(cls, db: AsyncDBSession) -> int:
        """Remove all expired sessions. Returns count deleted."""
        result = await db.execute(
            delete(cls).where(cls.expires_at < datetime.now(timezone.utc))
        )
        await db.commit()
        return result.rowcount
