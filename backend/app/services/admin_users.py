from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.admin_user import AdminUserCreate, AdminUserUpdate
from app.services.audit import write_audit_log
from app.services.users import get_user_by_username


def list_admin_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.role, User.username, User.id)))


def create_admin_user(
    db: Session,
    *,
    payload: AdminUserCreate,
    actor: User,
) -> User:
    if get_user_by_username(db, payload.username) is not None:
        raise ValueError("Bu kullanici adi zaten kullaniliyor.")

    user = User(
        username=payload.username,
        full_name=payload.full_name,
        role=payload.role,
        password_hash=hash_password(payload.password),
        is_active=payload.is_active,
    )
    db.add(user)
    db.flush()
    write_audit_log(
        db,
        actor=actor,
        action="USER_CREATED",
        target_type="users",
        target_id=user.id,
        description=f"{actor.username} kullanici olusturdu: {user.username}",
    )
    db.commit()
    db.refresh(user)
    return user


def update_admin_user(
    db: Session,
    *,
    user_id: int,
    payload: AdminUserUpdate,
    actor: User,
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise ValueError("Kullanici bulunamadi.")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return user

    validate_self_update(user=user, actor=actor, data=data)

    if "full_name" in data and data["full_name"] is not None:
        user.full_name = data["full_name"]
    if "role" in data and data["role"] is not None:
        user.role = data["role"]
    if "is_active" in data and data["is_active"] is not None:
        user.is_active = data["is_active"]
    if "password" in data and data["password"]:
        user.password_hash = hash_password(data["password"])

    write_audit_log(
        db,
        actor=actor,
        action="USER_UPDATED",
        target_type="users",
        target_id=user.id,
        description=f"{actor.username} kullanici guncelledi: {user.username}",
    )
    db.commit()
    db.refresh(user)
    return user


def validate_self_update(*, user: User, actor: User, data: dict[str, object]) -> None:
    if user.id != actor.id:
        return

    if data.get("is_active") is False:
        raise ValueError("Kendi hesabinizi pasife alamazsiniz.")

    if data.get("role") not in (None, "ADMIN"):
        raise ValueError("Kendi admin yetkinizi kaldiramazsiniz.")
