from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_number: Mapped[str | None] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="NEW")
    customer_first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    customer_last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    delivery_area_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_areas.id"),
        nullable=False,
        index=True,
    )
    delivery_area_name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    neighborhood: Mapped[str] = mapped_column(String(120), nullable=False)
    street: Mapped[str] = mapped_column(String(160), nullable=False)
    apartment: Mapped[str | None] = mapped_column(String(80), nullable=True)
    flat: Mapped[str | None] = mapped_column(String(40), nullable=True)
    address_line: Mapped[str] = mapped_column(String(500), nullable=False)
    address_directions: Mapped[str | None] = mapped_column(String(500), nullable=True)
    order_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False)
    unavailable_policy: Mapped[str] = mapped_column(String(32), nullable=False)
    cancellation_reason: Mapped[str | None] = mapped_column(String(160), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
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

    delivery_area: Mapped["DeliveryArea"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    product_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    order: Mapped["Order"] = relationship(back_populates="items")
