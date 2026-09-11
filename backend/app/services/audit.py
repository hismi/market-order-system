from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


def write_audit_log(
    db: Session,
    *,
    actor: User,
    action: str,
    target_type: str,
    target_id: int | None,
    description: str,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            actor_username_snapshot=actor.username,
            action=action,
            target_type=target_type,
            target_id=target_id,
            description=description,
        )
    )


def list_audit_logs(db: Session, *, limit: int = 100) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
        )
    )
