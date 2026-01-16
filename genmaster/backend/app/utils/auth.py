# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/utils/auth.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Authentication utilities for JWT tokens and password hashing."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.hash import bcrypt

from app.config import settings

# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return bcrypt.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to check against

    Returns:
        True if password matches
    """
    try:
        return bcrypt.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(
    user_id: int,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, datetime]:
    """
    Create a JWT access token.

    Args:
        user_id: User ID to encode in token
        expires_delta: Optional custom expiry time

    Returns:
        Tuple of (token string, expiry datetime)
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            hours=ACCESS_TOKEN_EXPIRE_HOURS
        )

    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    encoded_jwt = jwt.encode(
        to_encode, settings.app_secret_key, algorithm=ALGORITHM
    )

    return encoded_jwt, expire


def decode_access_token(token: str) -> Optional[int]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string

    Returns:
        User ID if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token, settings.app_secret_key, algorithms=[ALGORITHM]
        )

        # Verify token type
        if payload.get("type") != "access":
            return None

        user_id = payload.get("sub")
        if user_id is None:
            return None

        return int(user_id)

    except JWTError:
        return None
    except (ValueError, TypeError):
        return None


def generate_session_token() -> str:
    """
    Generate a secure random session token.

    Returns:
        64-character hex token
    """
    return secrets.token_hex(32)


def get_token_expiry_seconds() -> int:
    """Get token expiry time in seconds."""
    return ACCESS_TOKEN_EXPIRE_HOURS * 3600
