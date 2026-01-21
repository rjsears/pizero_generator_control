# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/redis_cache.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 20th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Redis cache service for frequently accessed data."""

import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

# Cache key constants
CACHE_KEY_CONFIG = "genmaster:config"
CACHE_KEY_GENERATOR_INFO = "genmaster:generator_info"
CACHE_KEY_SESSION_PREFIX = "genmaster:session:"

# TTL constants (seconds)
TTL_CONFIG = 300  # 5 minutes
TTL_GENERATOR_INFO = 300  # 5 minutes
TTL_SESSION = 86400  # 24 hours (matches session expiry)


class RedisCacheService:
    """
    Redis cache service for caching frequently accessed data.

    Caches:
    - Config: Read every 1s poll, rarely changes. ~99% DB reduction.
    - GeneratorInfo: Read on dashboard, fuel calcs. Rarely changes.
    - Sessions: Read on every authenticated request. Faster than DB.
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis cache service.

        Args:
            redis_url: Redis connection URL (default from settings)
        """
        self._redis_url = redis_url or settings.redis_url
        self._client: Optional[redis.Redis] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected

    async def connect(self) -> bool:
        """
        Connect to Redis server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._client = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info(f"Redis connected: {self._redis_url}")
            return True
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Falling back to database.")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        if self._client:
            await self._client.close()
            self._client = None
            self._connected = False
            logger.info("Redis disconnected")

    # =========================================================================
    # Config Cache Methods
    # =========================================================================

    async def get_config(self) -> Optional[dict[str, Any]]:
        """
        Get cached config from Redis.

        Returns:
            Config dict if cached, None if not cached or Redis unavailable
        """
        if not self._connected or not self._client:
            return None

        try:
            data = await self._client.get(CACHE_KEY_CONFIG)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.debug(f"Redis get_config error: {e}")
            return None

    async def set_config(self, config_data: dict[str, Any]) -> bool:
        """
        Cache config data in Redis.

        Args:
            config_data: Config dictionary to cache

        Returns:
            True if cached successfully, False otherwise
        """
        if not self._connected or not self._client:
            return False

        try:
            await self._client.set(
                CACHE_KEY_CONFIG,
                json.dumps(config_data),
                ex=TTL_CONFIG,
            )
            logger.debug("Config cached in Redis")
            return True
        except Exception as e:
            logger.debug(f"Redis set_config error: {e}")
            return False

    async def invalidate_config(self) -> bool:
        """
        Invalidate (delete) cached config.

        Call this when config is updated to ensure fresh data.

        Returns:
            True if invalidated successfully, False otherwise
        """
        if not self._connected or not self._client:
            return False

        try:
            await self._client.delete(CACHE_KEY_CONFIG)
            logger.info("Config cache invalidated")
            return True
        except Exception as e:
            logger.debug(f"Redis invalidate_config error: {e}")
            return False

    # =========================================================================
    # GeneratorInfo Cache Methods
    # =========================================================================

    async def get_generator_info(self) -> Optional[dict[str, Any]]:
        """
        Get cached generator info from Redis.

        Returns:
            GeneratorInfo dict if cached, None if not cached
        """
        if not self._connected or not self._client:
            return None

        try:
            data = await self._client.get(CACHE_KEY_GENERATOR_INFO)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.debug(f"Redis get_generator_info error: {e}")
            return None

    async def set_generator_info(self, info_data: dict[str, Any]) -> bool:
        """
        Cache generator info in Redis.

        Args:
            info_data: GeneratorInfo dictionary to cache

        Returns:
            True if cached successfully, False otherwise
        """
        if not self._connected or not self._client:
            return False

        try:
            await self._client.set(
                CACHE_KEY_GENERATOR_INFO,
                json.dumps(info_data),
                ex=TTL_GENERATOR_INFO,
            )
            logger.debug("GeneratorInfo cached in Redis")
            return True
        except Exception as e:
            logger.debug(f"Redis set_generator_info error: {e}")
            return False

    async def invalidate_generator_info(self) -> bool:
        """
        Invalidate cached generator info.

        Call this when generator info is updated.

        Returns:
            True if invalidated successfully, False otherwise
        """
        if not self._connected or not self._client:
            return False

        try:
            await self._client.delete(CACHE_KEY_GENERATOR_INFO)
            logger.info("GeneratorInfo cache invalidated")
            return True
        except Exception as e:
            logger.debug(f"Redis invalidate_generator_info error: {e}")
            return False

    # =========================================================================
    # Session Cache Methods
    # =========================================================================

    async def get_session(self, token: str) -> Optional[dict[str, Any]]:
        """
        Get cached session by token.

        Args:
            token: Session token

        Returns:
            Session dict if cached, None if not cached
        """
        if not self._connected or not self._client:
            return None

        try:
            key = f"{CACHE_KEY_SESSION_PREFIX}{token}"
            data = await self._client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.debug(f"Redis get_session error: {e}")
            return None

    async def set_session(
        self,
        token: str,
        session_data: dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache session data.

        Args:
            token: Session token (used as key)
            session_data: Session dictionary to cache
            ttl: Time-to-live in seconds (default: 24 hours)

        Returns:
            True if cached successfully, False otherwise
        """
        if not self._connected or not self._client:
            return False

        try:
            key = f"{CACHE_KEY_SESSION_PREFIX}{token}"
            await self._client.set(
                key,
                json.dumps(session_data),
                ex=ttl or TTL_SESSION,
            )
            logger.debug(f"Session cached in Redis: {token[:8]}...")
            return True
        except Exception as e:
            logger.debug(f"Redis set_session error: {e}")
            return False

    async def invalidate_session(self, token: str) -> bool:
        """
        Invalidate (delete) a cached session.

        Call this on logout.

        Args:
            token: Session token to invalidate

        Returns:
            True if invalidated successfully, False otherwise
        """
        if not self._connected or not self._client:
            return False

        try:
            key = f"{CACHE_KEY_SESSION_PREFIX}{token}"
            await self._client.delete(key)
            logger.debug(f"Session cache invalidated: {token[:8]}...")
            return True
        except Exception as e:
            logger.debug(f"Redis invalidate_session error: {e}")
            return False

    async def invalidate_user_sessions(self, user_id: int) -> int:
        """
        Invalidate all sessions for a user.

        This requires scanning keys, which is expensive.
        For production, consider storing user_id -> tokens mapping.

        Args:
            user_id: User ID whose sessions to invalidate

        Returns:
            Number of sessions invalidated
        """
        if not self._connected or not self._client:
            return 0

        try:
            # Scan for all session keys
            count = 0
            async for key in self._client.scan_iter(f"{CACHE_KEY_SESSION_PREFIX}*"):
                data = await self._client.get(key)
                if data:
                    session = json.loads(data)
                    if session.get("user_id") == user_id:
                        await self._client.delete(key)
                        count += 1
            logger.info(f"Invalidated {count} sessions for user {user_id}")
            return count
        except Exception as e:
            logger.debug(f"Redis invalidate_user_sessions error: {e}")
            return 0

    # =========================================================================
    # Generic Cache Methods
    # =========================================================================

    async def get(self, key: str) -> Optional[str]:
        """Get a value from cache."""
        if not self._connected or not self._client:
            return None

        try:
            return await self._client.get(key)
        except Exception as e:
            logger.debug(f"Redis get error for {key}: {e}")
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set a value in cache with optional TTL."""
        if not self._connected or not self._client:
            return False

        try:
            await self._client.set(key, value, ex=ttl)
            return True
        except Exception as e:
            logger.debug(f"Redis set error for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if not self._connected or not self._client:
            return False

        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.debug(f"Redis delete error for {key}: {e}")
            return False


# =========================================================================
# Singleton Instance
# =========================================================================

_cache_instance: Optional[RedisCacheService] = None


def get_redis_cache() -> RedisCacheService:
    """Get or create the singleton RedisCacheService instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCacheService()
    return _cache_instance


# =========================================================================
# Helper Functions - Config
# =========================================================================


async def get_cached_config() -> Optional[dict[str, Any]]:
    """
    Get config from Redis cache, falling back to database if not cached.

    This is the main function services should call to get config.
    It handles the cache-aside pattern:
    1. Try to get from cache
    2. If cache miss, get from DB and populate cache
    3. Return config

    Returns:
        Config dictionary or None
    """
    from app.database import AsyncSessionLocal
    from app.models import Config
    from sqlalchemy.future import select

    cache = get_redis_cache()

    # Try cache first
    cached = await cache.get_config()
    if cached:
        logger.debug("Config cache hit")
        return cached

    # Cache miss - fetch from database
    logger.debug("Config cache miss - fetching from database")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Config).where(Config.id == 1))
        config = result.scalar_one_or_none()

        if config:
            # Convert to dict for caching
            config_dict = {
                "id": config.id,
                "slave_api_url": config.slave_api_url,
                "slave_api_secret": config.slave_api_secret,
                "genslave_ip": config.genslave_ip,
                "genslave_hostname": config.genslave_hostname,
                "heartbeat_interval_seconds": config.heartbeat_interval_seconds,
                "failsafe_timeout_seconds": config.failsafe_timeout_seconds,
                "min_run_minutes": config.min_run_minutes,
                "max_run_minutes": config.max_run_minutes,
                "cooldown_minutes": config.cooldown_minutes,
                "runtime_limits_enabled": config.runtime_limits_enabled,
                "max_runtime_action": config.max_runtime_action,
                "cooldown_duration_minutes": config.cooldown_duration_minutes,
                "webhook_url": config.webhook_url,
                "webhook_secret": config.webhook_secret,
                "webhook_enabled": config.webhook_enabled,
            }

            # Populate cache
            await cache.set_config(config_dict)
            return config_dict

    return None


async def invalidate_config_cache() -> None:
    """Invalidate the config cache. Call after any config update."""
    cache = get_redis_cache()
    await cache.invalidate_config()


# =========================================================================
# Helper Functions - GeneratorInfo
# =========================================================================


async def get_cached_generator_info() -> Optional[dict[str, Any]]:
    """
    Get generator info from Redis cache, falling back to database.

    Returns:
        GeneratorInfo dictionary or None
    """
    from app.database import AsyncSessionLocal
    from app.models import GeneratorInfo
    from sqlalchemy.future import select

    cache = get_redis_cache()

    # Try cache first
    cached = await cache.get_generator_info()
    if cached:
        logger.debug("GeneratorInfo cache hit")
        return cached

    # Cache miss - fetch from database
    logger.debug("GeneratorInfo cache miss - fetching from database")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(GeneratorInfo).where(GeneratorInfo.id == 1))
        info = result.scalar_one_or_none()

        if info:
            info_dict = {
                "id": info.id,
                "manufacturer": info.manufacturer,
                "model_number": info.model_number,
                "serial_number": info.serial_number,
                "fuel_type": info.fuel_type,
                "load_expected": info.load_expected,
                "fuel_consumption_50": info.fuel_consumption_50,
                "fuel_consumption_100": info.fuel_consumption_100,
            }

            # Populate cache
            await cache.set_generator_info(info_dict)
            return info_dict

    return None


async def invalidate_generator_info_cache() -> None:
    """Invalidate the generator info cache. Call after any update."""
    cache = get_redis_cache()
    await cache.invalidate_generator_info()


# =========================================================================
# Helper Functions - Sessions
# =========================================================================


async def get_cached_session(token: str) -> Optional[dict[str, Any]]:
    """
    Get session from Redis cache, falling back to database.

    Args:
        token: Session token

    Returns:
        Session dictionary with user_id, or None if not found/expired
    """
    from app.database import AsyncSessionLocal
    from app.models import Session
    from sqlalchemy.future import select
    from datetime import datetime, timezone

    cache = get_redis_cache()

    # Try cache first
    cached = await cache.get_session(token)
    if cached:
        # Check if expired
        expires_at = datetime.fromisoformat(cached["expires_at"])
        if expires_at > datetime.now(timezone.utc):
            logger.debug("Session cache hit")
            return cached
        else:
            # Expired - invalidate cache
            await cache.invalidate_session(token)
            return None

    # Cache miss - fetch from database
    logger.debug("Session cache miss - fetching from database")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Session).where(Session.token == token))
        session = result.scalar_one_or_none()

        if session and session.expires_at > datetime.now(timezone.utc):
            session_dict = {
                "id": session.id,
                "user_id": session.user_id,
                "token": session.token,
                "expires_at": session.expires_at.isoformat(),
                "created_at": session.created_at.isoformat(),
            }

            # Calculate TTL based on expiry
            ttl = int((session.expires_at - datetime.now(timezone.utc)).total_seconds())
            if ttl > 0:
                await cache.set_session(token, session_dict, ttl)

            return session_dict

    return None


async def cache_session(
    token: str,
    user_id: int,
    expires_at: str,
    created_at: str,
    session_id: int,
) -> None:
    """
    Cache a new session after login.

    Args:
        token: Session token
        user_id: User ID
        expires_at: Expiry datetime ISO string
        created_at: Created datetime ISO string
        session_id: Session record ID
    """
    from datetime import datetime, timezone

    cache = get_redis_cache()

    session_dict = {
        "id": session_id,
        "user_id": user_id,
        "token": token,
        "expires_at": expires_at,
        "created_at": created_at,
    }

    # Calculate TTL
    expires = datetime.fromisoformat(expires_at)
    ttl = int((expires - datetime.now(timezone.utc)).total_seconds())
    if ttl > 0:
        await cache.set_session(token, session_dict, ttl)


async def invalidate_session_cache(token: str) -> None:
    """Invalidate a session from cache (on logout)."""
    cache = get_redis_cache()
    await cache.invalidate_session(token)


async def invalidate_user_sessions_cache(user_id: int) -> None:
    """Invalidate all sessions for a user from cache."""
    cache = get_redis_cache()
    await cache.invalidate_user_sessions(user_id)
