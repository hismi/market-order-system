from datetime import time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class PublicMarketSettingsRead(BaseModel):
    market_name: str
    phone: str | None = None
    whatsapp_number: str | None = None
    is_open: bool
    opening_time: time | None = None
    closing_time: time | None = None
    accepting_orders: bool
    closed_reason: str | None = None
    timezone: str
    minimum_order_amount: Decimal
    delivery_fee: Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("minimum_order_amount", "delivery_fee")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class MarketSettingsRead(PublicMarketSettingsRead):
    id: int


class MarketSettingsUpdate(BaseModel):
    market_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    whatsapp_number: str | None = Field(default=None, max_length=32)
    is_open: bool
    opening_time: time | None = None
    closing_time: time | None = None
    minimum_order_amount: Decimal = Field(ge=0, le=100000)
    delivery_fee: Decimal = Field(ge=0, le=10000)

    @field_validator("market_name", "phone", "whatsapp_number", mode="before")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None

    @field_validator("phone", "whatsapp_number")
    @classmethod
    def validate_phone_like_value(cls, value: str | None) -> str | None:
        if value is None:
            return None

        allowed_chars = set("0123456789+ ()-")
        if any(char not in allowed_chars for char in value):
            raise ValueError("Telefon alani gecersiz karakter iceriyor.")

        digit_count = sum(char.isdigit() for char in value)
        if digit_count < 10 or digit_count > 15:
            raise ValueError("Telefon alani 10-15 rakam icermelidir.")

        return value
