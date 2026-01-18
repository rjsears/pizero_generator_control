# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genslave/app/auth.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 18th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""API authentication for GenSlave."""

import logging
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.services.database import db_service

logger = logging.getLogger(__name__)

# API key header - GenMaster must send this header with requests
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_current_api_secret() -> Optional[str]:
    """Get the current API secret from database.

    Returns:
        The API secret or None if not configured.
    """
    return db_service.get_api_secret()


async def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """
    Verify the API key from the X-API-Key header.

    This dependency should be added to routes that require authentication.
    Reads the expected API secret from the database, allowing runtime updates
    without container restarts.

    Raises:
        HTTPException: If API key is missing or invalid

    Returns:
        The validated API key
    """
    # Get the current API secret from database
    expected_secret = get_current_api_secret()

    # If no API secret is configured, allow all requests (development mode)
    if not expected_secret:
        logger.warning("API_SECRET not configured - authentication disabled")
        return ""

    if not api_key:
        logger.warning("API request rejected - missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    if api_key != expected_secret:
        logger.warning("API request rejected - invalid API key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key


async def verify_api_key_optional(
    api_key: Optional[str] = Security(API_KEY_HEADER)
) -> Optional[str]:
    """
    Optional API key verification - logs but doesn't reject if missing.

    Use this for endpoints that should work without auth but log access.
    """
    expected_secret = get_current_api_secret()

    if expected_secret and api_key and api_key != expected_secret:
        logger.warning("API request with invalid key - rejecting")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key
