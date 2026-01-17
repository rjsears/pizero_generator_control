# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/auth.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Authentication API endpoints."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.future import select

from app.dependencies import CurrentUser, DbSession
from app.models import Session, User
from app.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    TokenResponse,
    UserResponse,
)
from app.utils.auth import (
    create_access_token,
    generate_session_token,
    get_token_expiry_seconds,
)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: DbSession,
) -> LoginResponse:
    """
    Authenticate user and return access token.
    """
    # Find user
    result = await db.execute(
        select(User).where(User.username == request.username)
    )
    user = result.scalar_one_or_none()

    if not user or not user.verify_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    # Create JWT token
    access_token, expires_at = create_access_token(user.id)

    # Create session record
    session = Session(
        user_id=user.id,
        token=generate_session_token(),
        expires_at=expires_at,
    )
    db.add(session)
    await db.commit()

    return LoginResponse(
        token=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=get_token_expiry_seconds(),
        ),
        user=UserResponse(
            id=user.id,
            username=user.username,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at.isoformat(),
        ),
    )


@router.post("/logout")
async def logout(
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Logout current user by invalidating all their sessions.
    """
    # Delete all sessions for this user
    result = await db.execute(
        select(Session).where(Session.user_id == current_user.id)
    )
    sessions = result.scalars().all()

    for session in sessions:
        await db.delete(session)

    await db.commit()

    return {"success": True, "message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser,
) -> UserResponse:
    """
    Get current authenticated user information.
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at.isoformat(),
    )


@router.put("/password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Change the current user's password.
    """
    # Verify current password
    if not current_user.verify_password(request.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.set_password(request.new_password)
    await db.commit()

    return {"success": True, "message": "Password changed successfully"}


@router.post("/cleanup")
async def cleanup_sessions(
    db: DbSession,
) -> dict:
    """
    Remove expired sessions.

    This is typically called by a scheduled task.
    """
    count = await Session.cleanup_expired(db)
    return {"success": True, "message": f"Removed {count} expired sessions"}
