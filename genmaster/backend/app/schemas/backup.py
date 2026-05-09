# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/schemas/backup.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Backup-related Pydantic schemas."""

from pydantic import BaseModel, Field


class BackupInfo(BaseModel):
    """Information about a backup file."""

    filename: str = Field(description="Backup filename")
    size_bytes: int = Field(description="File size in bytes")
    created_at: str = Field(description="ISO timestamp when backup was created")


class BackupResponse(BaseModel):
    """Response after creating a backup."""

    success: bool
    message: str
    backup: BackupInfo = Field(description="Information about the created backup")


class BackupListResponse(BaseModel):
    """Response listing available backups."""

    backups: list[BackupInfo] = Field(description="List of available backups")
    total_count: int = Field(description="Total number of backups")
    total_size_bytes: int = Field(description="Total size of all backups in bytes")
