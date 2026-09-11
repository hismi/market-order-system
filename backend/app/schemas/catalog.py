from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer


class CategoryRead(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    display_order: int

    model_config = ConfigDict(from_attributes=True)


class CategorySummary(BaseModel):
    id: int
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


class ProductRead(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    image_url: str | None = None
    price: Decimal
    stock_quantity: int
    is_in_stock: bool
    category: CategorySummary | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("price")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"
