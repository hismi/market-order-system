from datetime import date
from decimal import Decimal

from pydantic import BaseModel, field_serializer


class DailyOrderReportItem(BaseModel):
    day: date
    order_count: int
    delivered_count: int
    cancelled_count: int
    revenue: Decimal
    delivery_fees: Decimal

    @field_serializer("revenue", "delivery_fees")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class TopProductReportItem(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    revenue: Decimal

    @field_serializer("revenue")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class OrderReportRead(BaseModel):
    start_date: date | None
    end_date: date | None
    total_orders: int
    new_orders: int
    preparing_orders: int
    on_the_way_orders: int
    delivered_orders: int
    cancelled_orders: int
    active_orders: int
    active_grand_total: Decimal
    delivered_revenue: Decimal
    delivered_subtotal: Decimal
    delivered_delivery_fees: Decimal
    average_delivered_order_total: Decimal
    top_products: list[TopProductReportItem]
    daily_totals: list[DailyOrderReportItem]

    @field_serializer(
        "active_grand_total",
        "delivered_revenue",
        "delivered_subtotal",
        "delivered_delivery_fees",
        "average_delivered_order_total",
    )
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"
