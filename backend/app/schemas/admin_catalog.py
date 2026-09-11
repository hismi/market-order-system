from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.schemas.catalog import CategorySummary


class CategoryWrite(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=2, max_length=140)
    description: str | None = Field(default=None, max_length=500)
    display_order: int = Field(default=0, ge=0, le=100000)
    is_active: bool = True

    @field_validator("name", "slug", "description", mode="before")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class AdminCategoryRead(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductWrite(BaseModel):
    category_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=2, max_length=160)
    slug: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=3000)
    sku: str | None = Field(default=None, max_length=80)
    image_url: str | None = Field(default=None, max_length=500)
    price: Decimal = Field(ge=0, le=1000000)
    stock_quantity: int = Field(ge=0, le=999999)
    is_active: bool = True

    @field_validator("name", "slug", "description", "sku", "image_url", mode="before")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class ProductImageUploadRead(BaseModel):
    image_url: str


class AdminProductRead(BaseModel):
    id: int
    category_id: int | None = None
    name: str
    slug: str
    description: str | None = None
    sku: str | None = None
    image_url: str | None = None
    price: Decimal
    stock_quantity: int
    is_active: bool
    is_in_stock: bool
    category: CategorySummary | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("price")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"
