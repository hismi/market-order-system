from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.database.session import get_db
from app.models.user import User
from app.schemas.admin_user import AdminUserCreate, AdminUserRead, AdminUserUpdate
from app.services.admin_users import (
    create_admin_user,
    list_admin_users,
    update_admin_user,
)

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


AdminUser = Depends(require_roles("ADMIN"))


@router.get("", response_model=list[AdminUserRead])
def read_admin_users(
    db: Session = Depends(get_db),
    current_user: User = AdminUser,
) -> list[User]:
    _ = current_user
    return list_admin_users(db)


@router.post("", response_model=AdminUserRead, status_code=status.HTTP_201_CREATED)
def create_managed_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user: User = AdminUser,
) -> User:
    try:
        return create_admin_user(db, payload=payload, actor=current_user)
    except ValueError as error:
        raise bad_request(error) from error


@router.patch("/{user_id}", response_model=AdminUserRead)
def update_managed_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = AdminUser,
) -> User:
    try:
        return update_admin_user(
            db,
            user_id=user_id,
            payload=payload,
            actor=current_user,
        )
    except ValueError as error:
        raise bad_request(error) from error


def bad_request(error: ValueError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": "ADMIN_USERS_REJECTED",
            "message": str(error),
        },
    )
