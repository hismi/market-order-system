from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.models.user import User
from app.schemas.admin_status import AdminSystemStatusRead
from app.services.admin_status import build_admin_system_status

router = APIRouter(prefix="/api/admin/system-status", tags=["admin-system-status"])


AdminUser = Depends(require_roles("ADMIN"))


@router.get("", response_model=AdminSystemStatusRead)
def read_admin_system_status(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: User = AdminUser,
) -> dict[str, object]:
    _ = current_user
    return build_admin_system_status(db, settings=settings)
