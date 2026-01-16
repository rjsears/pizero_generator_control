# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/backup.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Database backup API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.dependencies import AdminUser, require_admin
from app.schemas import BackupInfo, BackupListResponse, BackupResponse
from app.services.backup import BackupService

router = APIRouter()


def get_backup_service() -> BackupService:
    """Get backup service instance."""
    return BackupService()


@router.post("", response_model=BackupResponse)
@router.post("/", response_model=BackupResponse)
async def create_backup(
    backup_service: BackupService = Depends(get_backup_service),
    admin: AdminUser = Depends(require_admin),
) -> BackupResponse:
    """
    Create a new database backup.

    Requires admin authentication.
    """
    try:
        backup = await backup_service.create_backup()
        return BackupResponse(
            success=True,
            message="Backup created successfully",
            backup=BackupInfo(
                filename=backup.filename,
                size_bytes=backup.size_bytes,
                created_at=backup.created_at.isoformat(),
            ),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=BackupListResponse)
@router.get("/", response_model=BackupListResponse)
async def list_backups(
    backup_service: BackupService = Depends(get_backup_service),
) -> BackupListResponse:
    """
    List all available backups.
    """
    backups = backup_service.list_backups()
    return BackupListResponse(
        backups=[
            BackupInfo(
                filename=b.filename,
                size_bytes=b.size_bytes,
                created_at=b.created_at.isoformat(),
            )
            for b in backups
        ],
        total_count=len(backups),
        total_size_bytes=backup_service.get_total_size(),
    )


@router.get("/download/{filename}")
async def download_backup(
    filename: str,
    backup_service: BackupService = Depends(get_backup_service),
    admin: AdminUser = Depends(require_admin),
) -> FileResponse:
    """
    Download a backup file.

    Requires admin authentication.
    """
    path = backup_service.get_backup_path(filename)

    if not path:
        raise HTTPException(status_code=404, detail="Backup not found")

    return FileResponse(
        path=path,
        filename=filename,
        media_type="application/sql",
    )


@router.delete("/{filename}")
async def delete_backup(
    filename: str,
    backup_service: BackupService = Depends(get_backup_service),
    admin: AdminUser = Depends(require_admin),
) -> dict:
    """
    Delete a backup file.

    Requires admin authentication.
    """
    if not backup_service.delete_backup(filename):
        raise HTTPException(status_code=404, detail="Backup not found")

    return {"success": True, "message": f"Backup {filename} deleted"}
