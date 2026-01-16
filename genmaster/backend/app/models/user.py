# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/models/user.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""User model - authentication users for the web UI."""

from datetime import datetime
from typing import TYPE_CHECKING, List

from passlib.hash import bcrypt
from sqlalchemy import Index, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.session import Session


class User(Base):
    """Stores user accounts for web UI authentication."""

    __tablename__ = "users"
    __table_args__ = (Index("idx_users_username", "username", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Authentication
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(nullable=False)

    # Profile
    is_active: Mapped[bool] = mapped_column(default=True)
    is_admin: Mapped[bool] = mapped_column(default=False)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    sessions: Mapped[List["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        """Hash and set password."""
        self.password_hash = bcrypt.hash(password)

    def verify_password(self, password: str) -> bool:
        """Verify password against hash."""
        return bcrypt.verify(password, self.password_hash)

    @classmethod
    async def create(
        cls,
        db: AsyncSession,
        username: str,
        password: str,
        is_admin: bool = False,
    ) -> "User":
        """Create a new user."""
        user = cls(username=username, is_admin=is_admin)
        user.set_password(password)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
