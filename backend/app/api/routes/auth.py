from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.config import Settings, get_settings
from app.core.security import create_access_token
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import (
    CurrentUserRead,
    LoginRequest,
    PasswordChangeRead,
    PasswordChangeRequest,
    TokenResponse,
)
from app.services.login_rate_limiter import (
    LoginRateLimitError,
    login_rate_limiter,
)
from app.services.users import authenticate_user, change_user_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    rate_limit_key = build_login_rate_limit_key(request, payload.username)

    try:
        login_rate_limiter.check_allowed(rate_limit_key, settings)
    except LoginRateLimitError as error:
        raise rate_limit_error(error) from error

    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        login_rate_limiter.record_failure(rate_limit_key, settings)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanici adi veya sifre hatali.",
        )

    login_rate_limiter.record_success(rate_limit_key)
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )
    return TokenResponse(
        access_token=token,
        role=user.role,
        username=user.username,
        full_name=user.full_name,
    )


@router.get("/me", response_model=CurrentUserRead)
def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me/password", response_model=PasswordChangeRead)
def update_my_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PasswordChangeRead:
    try:
        change_user_password(
            db,
            user=current_user,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "PASSWORD_CHANGE_REJECTED",
                "message": str(error),
            },
        ) from error

    return PasswordChangeRead(message="Sifre guncellendi.")


def build_login_rate_limit_key(request: Request, username: str) -> str:
    client_host = request.client.host if request.client is not None else "unknown"
    return f"{client_host}:{username.strip().lower()}"


def rate_limit_error(error: LoginRateLimitError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "code": "LOGIN_RATE_LIMITED",
            "message": "Cok fazla hatali giris denemesi. Lutfen biraz sonra tekrar deneyin.",
            "retry_after_seconds": error.retry_after_seconds,
        },
        headers={"Retry-After": str(error.retry_after_seconds)},
    )
