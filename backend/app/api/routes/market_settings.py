from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.models.user import User
from app.schemas.market_settings import (
    MarketSettingsRead,
    MarketSettingsUpdate,
    PublicMarketSettingsRead,
)
from app.services.market_settings import (
    build_market_settings_response,
    get_market_settings,
    update_market_settings,
)

router = APIRouter(prefix="/api/market-settings", tags=["market-settings"])


@router.get("/public", response_model=PublicMarketSettingsRead)
def read_public_market_settings(
    db: Session = Depends(get_db),
    app_settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return build_market_settings_response(
        get_market_settings(db),
        app_settings=app_settings,
    )


@router.get("/admin", response_model=MarketSettingsRead)
def read_admin_market_settings(
    db: Session = Depends(get_db),
    app_settings: Settings = Depends(get_settings),
    current_user: User = Depends(require_roles("ADMIN")),
) -> dict[str, object]:
    _ = current_user
    return build_market_settings_response(
        get_market_settings(db),
        app_settings=app_settings,
    )


@router.patch("/admin", response_model=MarketSettingsRead)
def update_admin_market_settings(
    payload: MarketSettingsUpdate,
    db: Session = Depends(get_db),
    app_settings: Settings = Depends(get_settings),
    current_user: User = Depends(require_roles("ADMIN")),
) -> dict[str, object]:
    market_settings = update_market_settings(db, payload=payload, actor=current_user)
    return build_market_settings_response(
        market_settings,
        app_settings=app_settings,
    )
