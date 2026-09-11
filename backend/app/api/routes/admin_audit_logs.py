from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.database.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogRead
from app.services.audit import list_audit_logs

router = APIRouter(prefix="/api/admin/audit-logs", tags=["admin-audit-logs"])


AdminUser = Depends(require_roles("ADMIN"))


@router.get("", response_model=list[AuditLogRead])
def read_audit_logs(
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = AdminUser,
) -> list[AuditLog]:
    _ = current_user
    return list_audit_logs(db, limit=limit)
