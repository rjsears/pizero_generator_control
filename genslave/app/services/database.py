# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genslave/app/services/database.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 18th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Database service for GenSlave settings storage."""

import asyncio
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """SQLite database service for storing GenSlave settings.

    Provides persistent storage for configuration that can be updated
    at runtime without requiring container restarts.
    """

    def __init__(self):
        self._db_path = settings.DATABASE_PATH
        self._cache: dict[str, str] = {}
        self._cache_lock = Lock()
        self._initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        """Initialize the database schema.

        Creates the settings table if it doesn't exist and seeds
        the API secret from environment variable if not already set.
        """
        if self._initialized:
            return

        # Ensure directory exists
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Create settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

            # Check if API secret exists in DB
            cursor.execute(
                "SELECT value FROM settings WHERE key = ?",
                ("api_secret",)
            )
            row = cursor.fetchone()

            if row:
                # Load from DB into cache
                self._cache["api_secret"] = row["value"]
                logger.info("API secret loaded from database")
            elif settings.API_SECRET:
                # Seed from environment variable
                self._set_setting_sync(conn, "api_secret", settings.API_SECRET)
                logger.info("API secret seeded from environment variable")
            else:
                # No API secret configured - this is a problem
                logger.warning(
                    "No API secret configured! GenSlave API is unprotected. "
                    "Set GENSLAVE_API_SECRET in .env file."
                )

            self._initialized = True
            logger.info(f"Database initialized: {self._db_path}")

        finally:
            conn.close()

    def _set_setting_sync(
        self, conn: sqlite3.Connection, key: str, value: str
    ) -> None:
        """Set a setting synchronously (used during init)."""
        now = datetime.utcnow().isoformat()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            """,
            (key, value, now)
        )
        conn.commit()

        with self._cache_lock:
            self._cache[key] = value

    def get_api_secret(self) -> Optional[str]:
        """Get the current API secret.

        Returns cached value if available, otherwise reads from database.

        Returns:
            The API secret or None if not configured.
        """
        with self._cache_lock:
            if "api_secret" in self._cache:
                return self._cache["api_secret"]

        # Read from database
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM settings WHERE key = ?",
                ("api_secret",)
            )
            row = cursor.fetchone()

            if row:
                with self._cache_lock:
                    self._cache["api_secret"] = row["value"]
                return row["value"]

            return None
        finally:
            conn.close()

    def set_api_secret(self, new_secret: str) -> bool:
        """Update the API secret.

        Updates both the database and the in-memory cache.
        Takes effect immediately - no restart required.

        Args:
            new_secret: The new API secret value.

        Returns:
            True if successful, False otherwise.
        """
        if not new_secret:
            logger.error("Cannot set empty API secret")
            return False

        conn = self._get_connection()
        try:
            self._set_setting_sync(conn, "api_secret", new_secret)
            logger.info("API secret updated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to update API secret: {e}")
            return False
        finally:
            conn.close()

    def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value by key.

        Args:
            key: The setting key.

        Returns:
            The setting value or None if not found.
        """
        with self._cache_lock:
            if key in self._cache:
                return self._cache[key]

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()

            if row:
                with self._cache_lock:
                    self._cache[key] = row["value"]
                return row["value"]

            return None
        finally:
            conn.close()

    def set_setting(self, key: str, value: str) -> bool:
        """Set a setting value.

        Args:
            key: The setting key.
            value: The setting value.

        Returns:
            True if successful, False otherwise.
        """
        conn = self._get_connection()
        try:
            self._set_setting_sync(conn, key, value)
            return True
        except Exception as e:
            logger.error(f"Failed to set setting {key}: {e}")
            return False
        finally:
            conn.close()

    def clear_cache(self) -> None:
        """Clear the in-memory cache.

        Forces next read to fetch from database.
        """
        with self._cache_lock:
            self._cache.clear()
        logger.debug("Settings cache cleared")


# Global database service instance
db_service = DatabaseService()
