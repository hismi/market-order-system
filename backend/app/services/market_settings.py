from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.market_settings import MarketSettings
from app.models.user import User
from app.schemas.market_settings import MarketSettingsUpdate
from app.services.audit import write_audit_log


def get_market_settings(db: Session) -> MarketSettings:
    settings = db.scalar(select(MarketSettings).limit(1))
    if settings is not None:
        return settings

    settings = MarketSettings(
        market_name="Yerel Market",
        is_open=True,
        minimum_order_amount=Decimal("300.00"),
        delivery_fee=Decimal("50.00"),
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def update_market_settings(
    db: Session,
    *,
    payload: MarketSettingsUpdate,
    actor: User,
) -> MarketSettings:
    settings = get_market_settings(db)
    old_values = {
        "market_name": settings.market_name,
        "phone": settings.phone,
        "whatsapp_number": settings.whatsapp_number,
        "is_open": settings.is_open,
        "opening_time": settings.opening_time,
        "closing_time": settings.closing_time,
        "minimum_order_amount": settings.minimum_order_amount,
        "delivery_fee": settings.delivery_fee,
    }

    settings.market_name = payload.market_name
    settings.phone = payload.phone
    settings.whatsapp_number = payload.whatsapp_number
    settings.is_open = payload.is_open
    settings.opening_time = payload.opening_time
    settings.closing_time = payload.closing_time
    settings.minimum_order_amount = payload.minimum_order_amount
    settings.delivery_fee = payload.delivery_fee

    changed_fields = [
        field_name
        for field_name, old_value in old_values.items()
        if old_value != getattr(settings, field_name)
    ]

    if changed_fields:
        write_audit_log(
            db,
            actor=actor,
            action="MARKET_SETTINGS_UPDATED",
            target_type="market_settings",
            target_id=settings.id,
            description=(
                f"{actor.username} market ayarlarini guncelledi: "
                f"{', '.join(changed_fields)}"
            ),
        )

    db.commit()
    db.refresh(settings)
    return settings
