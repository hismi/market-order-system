from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_serializer


class AdminSystemStatusRead(BaseModel):
    checked_at: datetime
    api_status: str
    app_env: str
    market_name: str
    market_is_open: bool
    minimum_order_amount: Decimal
    delivery_fee: Decimal
    delivery_fee_always_charged: bool
    online_payment_enabled: bool
    whatsapp_mode: str
    category_count: int
    active_category_count: int
    product_count: int
    active_product_count: int
    out_of_stock_product_count: int
    low_stock_product_count: int
    delivery_area_count: int
    active_delivery_area_count: int
    total_orders: int
    active_orders: int
    new_orders: int
    preparing_orders: int
    on_the_way_orders: int
    delivered_orders: int
    cancelled_orders: int
    last_order_number: str | None
    last_order_at: datetime | None
    last_audit_action: str | None
    last_audit_at: datetime | None
    last_backup_action: str | None
    last_backup_at: datetime | None
    has_default_admin_username: bool
    has_default_employee_username: bool

    @field_serializer("minimum_order_amount", "delivery_fee")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"
