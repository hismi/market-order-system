from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class MarketSettings(Base):
    __tablename__ = "market_settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    market_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="Yerel Market",
    )
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    whatsapp_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    opening_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    closing_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    minimum_order_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("300.00"),
    )
    delivery_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("50.00"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
