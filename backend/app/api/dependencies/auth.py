from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.user import User
from app.services.users import get_user_by_id

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise_auth_error()

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise_auth_error()

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.isdigit():
        raise_auth_error()

    user = get_user_by_id(db, int(subject))
    if user is None or not user.is_active:
        raise_auth_error()

    return user


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu islem icin yetkiniz yok.",
            )
        return current_user

    return dependency


def raise_auth_error() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Gecerli giris token'i gerekli.",
        headers={"WWW-Authenticate": "Bearer"},
    )
