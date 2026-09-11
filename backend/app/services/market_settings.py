from dataclasses import dataclass
from datetime import datetime, time, timezone, tzinfo
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.market_settings import MarketSettings
from app.models.user import User
from app.schemas.market_settings import MarketSettingsUpdate
from app.services.audit import write_audit_log

MANUALLY_CLOSED_REASON = "MANUALLY_CLOSED"
OUTSIDE_WORKING_HOURS_REASON = "OUTSIDE_WORKING_HOURS"


@dataclass(frozen=True)
class MarketAcceptanceStatus:
    accepting_orders: bool
    closed_reason: str | None
    current_time: datetime
    timezone: str


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


def get_market_acceptance_status(
    market_settings: MarketSettings,
    *,
    app_settings: Settings | None = None,
    now: datetime | None = None,
) -> MarketAcceptanceStatus:
    settings = app_settings or get_settings()
    market_timezone = get_market_timezone(settings)
    current_time = normalize_current_time(
        now or get_current_market_datetime(settings),
        market_timezone,
    )

    if not market_settings.is_open:
        return MarketAcceptanceStatus(
            accepting_orders=False,
            closed_reason=MANUALLY_CLOSED_REASON,
            current_time=current_time,
            timezone=settings.app_timezone,
        )

    if not is_inside_working_hours(
        current_time.time(),
        market_settings.opening_time,
        market_settings.closing_time,
    ):
        return MarketAcceptanceStatus(
            accepting_orders=False,
            closed_reason=OUTSIDE_WORKING_HOURS_REASON,
            current_time=current_time,
            timezone=settings.app_timezone,
        )

    return MarketAcceptanceStatus(
        accepting_orders=True,
        closed_reason=None,
        current_time=current_time,
        timezone=settings.app_timezone,
    )


def is_market_accepting_orders(
    market_settings: MarketSettings,
    *,
    app_settings: Settings | None = None,
    now: datetime | None = None,
) -> bool:
    return get_market_acceptance_status(
        market_settings,
        app_settings=app_settings,
        now=now,
    ).accepting_orders


def build_market_settings_response(
    market_settings: MarketSettings,
    *,
    app_settings: Settings | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    acceptance_status = get_market_acceptance_status(
        market_settings,
        app_settings=app_settings,
        now=now,
    )

    return {
        "id": market_settings.id,
        "market_name": market_settings.market_name,
        "phone": market_settings.phone,
        "whatsapp_number": market_settings.whatsapp_number,
        "is_open": market_settings.is_open,
        "opening_time": market_settings.opening_time,
        "closing_time": market_settings.closing_time,
        "accepting_orders": acceptance_status.accepting_orders,
        "closed_reason": acceptance_status.closed_reason,
        "timezone": acceptance_status.timezone,
        "minimum_order_amount": market_settings.minimum_order_amount,
        "delivery_fee": market_settings.delivery_fee,
    }


def get_current_market_datetime(settings: Settings) -> datetime:
    return datetime.now(get_market_timezone(settings))


def get_market_timezone(settings: Settings) -> tzinfo:
    try:
        return ZoneInfo(settings.app_timezone)
    except ZoneInfoNotFoundError:
        return timezone.utc


def normalize_current_time(current_time: datetime, market_timezone: tzinfo) -> datetime:
    if current_time.tzinfo is None:
        return current_time.replace(tzinfo=market_timezone)
    return current_time.astimezone(market_timezone)


def is_inside_working_hours(
    current_time: time,
    opening_time: time | None,
    closing_time: time | None,
) -> bool:
    if opening_time is None and closing_time is None:
        return True

    if opening_time is not None and closing_time is not None:
        if opening_time == closing_time:
            return True
        if opening_time < closing_time:
            return opening_time <= current_time < closing_time
        return current_time >= opening_time or current_time < closing_time

    if opening_time is not None:
        return current_time >= opening_time

    return closing_time is None or current_time < closing_time


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
