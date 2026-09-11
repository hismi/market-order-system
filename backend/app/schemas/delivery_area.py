from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeliveryAreaRead(BaseModel):
    id: int
    name: str
    slug: str
    display_order: int

    model_config = ConfigDict(from_attributes=True)


class DeliveryAreaWrite(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=2, max_length=140)
    display_order: int = Field(default=0, ge=0, le=100000)
    is_active: bool = True

    @field_validator("name", "slug", mode="before")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class AdminDeliveryAreaRead(DeliveryAreaRead):
    is_active: bool
    created_at: datetime
    updated_at: datetime
