from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

PaymentMethod = Literal["CASH_ON_DELIVERY", "CARD_ON_DELIVERY"]
UnavailablePolicy = Literal["CALL_CUSTOMER", "REMOVE_ITEM", "SEND_SIMILAR"]


class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=99)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(min_length=1, max_length=60)
    customer_first_name: str = Field(min_length=2, max_length=80)
    customer_last_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=10, max_length=32)
    delivery_area_id: int = Field(gt=0)
    neighborhood: str = Field(min_length=2, max_length=120)
    street: str = Field(min_length=2, max_length=160)
    apartment: str | None = Field(default=None, max_length=80)
    flat: str | None = Field(default=None, max_length=40)
    address_line: str = Field(min_length=10, max_length=500)
    address_directions: str | None = Field(default=None, max_length=500)
    order_note: str | None = Field(default=None, max_length=500)
    payment_method: PaymentMethod
    unavailable_policy: UnavailablePolicy

    model_config = ConfigDict(extra="ignore")

    @field_validator(
        "customer_first_name",
        "customer_last_name",
        "phone",
        "neighborhood",
        "street",
        "apartment",
        "flat",
        "address_line",
        "address_directions",
        "order_note",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        allowed_chars = set("0123456789+ ()-")
        if any(char not in allowed_chars for char in value):
            raise ValueError("Telefon numarasi gecersiz karakter iceriyor.")

        digit_count = sum(char.isdigit() for char in value)
        if digit_count < 10 or digit_count > 15:
            raise ValueError("Telefon numarasi 10-15 rakam icermelidir.")

        return value


class OrderItemRead(BaseModel):
    product_id: int
    product_name_snapshot: str
    unit_price_snapshot: Decimal
    quantity: int
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("unit_price_snapshot", "line_total")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class PublicOrderItemRead(BaseModel):
    product_name_snapshot: str
    unit_price_snapshot: Decimal
    quantity: int
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("unit_price_snapshot", "line_total")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class OrderCreateResponse(BaseModel):
    order_number: str
    status: str
    subtotal: Decimal
    delivery_fee: Decimal
    grand_total: Decimal
    payment_method: str
    unavailable_policy: str
    items: list[PublicOrderItemRead]

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("subtotal", "delivery_fee", "grand_total")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class OrderTrackRead(BaseModel):
    order_number: str
    status: str
    customer_name: str
    phone: str
    delivery_area: str
    payment_method: str
    unavailable_policy: str
    cancellation_reason: str | None = None
    subtotal: Decimal
    delivery_fee: Decimal
    grand_total: Decimal
    created_at: datetime
    items: list[PublicOrderItemRead]

    @field_serializer("subtotal", "delivery_fee", "grand_total")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class EmployeeOrderRead(BaseModel):
    id: int
    order_number: str
    status: str
    customer_first_name: str
    customer_last_name: str
    phone: str
    delivery_area_name_snapshot: str
    neighborhood: str
    street: str
    apartment: str | None = None
    flat: str | None = None
    address_line: str
    address_directions: str | None = None
    order_note: str | None = None
    payment_method: str
    unavailable_policy: str
    cancellation_reason: str | None = None
    subtotal: Decimal
    delivery_fee: Decimal
    grand_total: Decimal
    created_at: datetime
    items: list[OrderItemRead]

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("subtotal", "delivery_fee", "grand_total")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class AdminOrderSummary(BaseModel):
    total_orders: int
    new_orders: int
    preparing_orders: int
    on_the_way_orders: int
    delivered_orders: int
    cancelled_orders: int
    active_orders: int
    active_grand_total: Decimal
    delivered_revenue: Decimal
    delivered_delivery_fees: Decimal

    @field_serializer(
        "active_grand_total",
        "delivered_revenue",
        "delivered_delivery_fees",
    )
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class RejectOrderRequest(BaseModel):
    reason: Literal[
        "OUT_OF_STOCK",
        "OUT_OF_DELIVERY_AREA",
        "BUSY",
        "CLOSING_SOON",
        "CUSTOMER_UNREACHABLE",
        "OTHER",
    ]
