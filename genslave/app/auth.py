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

from app.config import settings

logger = logging.getLogger(__name__)

# API key header - GenMaster must send this header with requests
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """
    Verify the API key from the X-API-Key header.

    This dependency should be added to routes that require authentication.

    Raises:
        HTTPException: If API key is missing or invalid

    Returns:
        The validated API key
    """
    # If no API secret is configured, allow all requests (development mode)
    if not settings.API_SECRET:
        logger.warning("API_SECRET not configured - authentication disabled")
        return ""

    if not api_key:
        logger.warning("API request rejected - missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    if api_key != settings.API_SECRET:
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
    if settings.API_SECRET and api_key and api_key != settings.API_SECRET:
        logger.warning("API request with invalid key - rejecting")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key
