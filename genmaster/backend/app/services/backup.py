# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/backup.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Backup service for database backup management."""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class BackupInfo:
    """Information about a backup file."""

    filename: str
    size_bytes: int
    created_at: datetime
    path: Path


class BackupService:
    """
    Manages PostgreSQL database backups using pg_dump.

    Backups are stored in /app/data/backups/ with timestamped filenames.
    """

    def __init__(self, backup_dir: Optional[str] = None):
        """
        Initialize backup service.

        Args:
            backup_dir: Directory for backups (default: /app/data/backups)
        """
        self.backup_dir = Path(backup_dir or "/app/data/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def create_backup(self) -> BackupInfo:
        """
        Create a new database backup.

        Returns:
            BackupInfo with details about the created backup

        Raises:
            RuntimeError: If backup fails
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"genmaster_backup_{timestamp}.sql"
        filepath = self.backup_dir / filename

        # Build pg_dump command
        cmd = [
            "pg_dump",
            "-h", settings.database_host,
            "-p", str(settings.database_port),
            "-U", settings.database_user,
            "-d", settings.database_name,
            "-f", str(filepath),
            "--no-password",
        ]

        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        env["PGPASSWORD"] = settings.database_password

        logger.info(f"Creating backup: {filename}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"pg_dump failed: {error}")

            # Get file info
            stat = filepath.stat()

            logger.info(
                f"Backup created: {filename} ({stat.st_size / 1024:.1f} KB)"
            )

            return BackupInfo(
                filename=filename,
                size_bytes=stat.st_size,
                created_at=datetime.utcnow(),
                path=filepath,
            )

        except FileNotFoundError:
            raise RuntimeError("pg_dump not found - is postgresql-client installed?")
        except Exception as e:
            # Clean up partial file
            if filepath.exists():
                filepath.unlink()
            raise RuntimeError(f"Backup failed: {e}")

    def list_backups(self) -> List[BackupInfo]:
        """
        List all available backups.

        Returns:
            List of BackupInfo sorted by creation time (newest first)
        """
        backups = []

        for filepath in self.backup_dir.glob("genmaster_backup_*.sql"):
            try:
                stat = filepath.stat()
                # Parse timestamp from filename
                timestamp_str = filepath.stem.replace("genmaster_backup_", "")
                created_at = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                backups.append(
                    BackupInfo(
                        filename=filepath.name,
                        size_bytes=stat.st_size,
                        created_at=created_at,
                        path=filepath,
                    )
                )
            except (ValueError, OSError) as e:
                logger.warning(f"Could not parse backup file {filepath}: {e}")

        # Sort by creation time, newest first
        backups.sort(key=lambda b: b.created_at, reverse=True)

        return backups

    def get_backup(self, filename: str) -> Optional[BackupInfo]:
        """
        Get information about a specific backup.

        Args:
            filename: Backup filename

        Returns:
            BackupInfo or None if not found
        """
        filepath = self.backup_dir / filename

        if not filepath.exists():
            return None

        if not filepath.name.startswith("genmaster_backup_"):
            return None

        try:
            stat = filepath.stat()
            timestamp_str = filepath.stem.replace("genmaster_backup_", "")
            created_at = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

            return BackupInfo(
                filename=filepath.name,
                size_bytes=stat.st_size,
                created_at=created_at,
                path=filepath,
            )
        except (ValueError, OSError):
            return None

    def get_backup_path(self, filename: str) -> Optional[Path]:
        """
        Get the full path to a backup file.

        Args:
            filename: Backup filename

        Returns:
            Path to backup file or None if not found
        """
        backup = self.get_backup(filename)
        return backup.path if backup else None

    def delete_backup(self, filename: str) -> bool:
        """
        Delete a backup file.

        Args:
            filename: Backup filename

        Returns:
            True if deleted, False if not found
        """
        filepath = self.backup_dir / filename

        if not filepath.exists():
            return False

        if not filepath.name.startswith("genmaster_backup_"):
            return False

        filepath.unlink()
        logger.info(f"Deleted backup: {filename}")
        return True

    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        Delete old backups, keeping the most recent ones.

        Args:
            keep_count: Number of backups to keep

        Returns:
            Number of backups deleted
        """
        backups = self.list_backups()

        if len(backups) <= keep_count:
            return 0

        deleted = 0
        for backup in backups[keep_count:]:
            if self.delete_backup(backup.filename):
                deleted += 1

        logger.info(f"Cleaned up {deleted} old backups")
        return deleted

    def get_total_size(self) -> int:
        """
        Get total size of all backups in bytes.

        Returns:
            Total size in bytes
        """
        return sum(b.size_bytes for b in self.list_backups())
