from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.models.user import User
from app.schemas.backup import BackupRestoreRead
from app.services.audit import write_audit_log
from app.services.backups import build_backup_archive, restore_backup_archive

router = APIRouter(prefix="/api/admin/backups", tags=["admin-backups"])


AdminUser = Depends(require_roles("ADMIN"))


@router.get("/export")
def export_backup(
    db: Session = Depends(get_db),
    current_user: User = AdminUser,
    settings: Settings = Depends(get_settings),
) -> Response:
    write_audit_log(
        db,
        actor=current_user,
        action="BACKUP_EXPORTED",
        target_type="backups",
        target_id=None,
        description=f"{current_user.username} sistem yedegi indirdi.",
    )
    db.commit()

    archive = build_backup_archive(db, upload_dir=Path(settings.upload_directory))
    filename = f"market-yedek-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    return Response(
        content=archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/restore", response_model=BackupRestoreRead)
def restore_backup(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = AdminUser,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    try:
        return restore_backup_archive(
            db,
            upload=file,
            upload_dir=Path(settings.upload_directory),
            max_bytes=settings.max_backup_upload_bytes,
            actor_username=current_user.username,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BACKUP_RESTORE_REJECTED",
                "message": str(error),
            },
        ) from error
