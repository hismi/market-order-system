from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.services.audit import write_audit_log


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username).limit(1))


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if user is None or not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def create_user(
    db: Session,
    *,
    username: str,
    password: str,
    full_name: str,
    role: str,
) -> User:
    user = User(
        username=username,
        full_name=full_name,
        role=role,
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def change_user_password(
    db: Session,
    *,
    user: User,
    current_password: str,
    new_password: str,
) -> User:
    if not verify_password(current_password, user.password_hash):
        raise ValueError("Mevcut sifre hatali.")

    if verify_password(new_password, user.password_hash):
        raise ValueError("Yeni sifre mevcut sifreden farkli olmalidir.")

    user.password_hash = hash_password(new_password)
    write_audit_log(
        db,
        actor=user,
        action="PASSWORD_CHANGED",
        target_type="users",
        target_id=user.id,
        description=f"{user.username} kendi sifresini degistirdi.",
    )
    db.commit()
    db.refresh(user)
    return user


def seed_users_if_configured(db: Session) -> None:
    settings = get_settings()

    if settings.seed_admin_username and settings.seed_admin_password:
        _create_seed_user_if_missing(
            db,
            username=settings.seed_admin_username,
            password=settings.seed_admin_password.get_secret_value(),
            full_name="Admin",
            role="ADMIN",
        )

    if settings.seed_employee_username and settings.seed_employee_password:
        _create_seed_user_if_missing(
            db,
            username=settings.seed_employee_username,
            password=settings.seed_employee_password.get_secret_value(),
            full_name="Market Calisani",
            role="EMPLOYEE",
        )


def _create_seed_user_if_missing(
    db: Session,
    *,
    username: str,
    password: str,
    full_name: str,
    role: str,
) -> None:
    existing_user = get_user_by_username(db, username)
    if existing_user is not None:
        return

    create_user(
        db,
        username=username,
        password=password,
        full_name=full_name,
        role=role,
    )
