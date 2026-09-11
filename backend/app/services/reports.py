from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order

ACTIVE_STATUSES = {"NEW", "PREPARING", "ON_THE_WAY"}


def build_order_report(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, object]:
    orders = get_orders_for_report(db, start_date=start_date, end_date=end_date)
    delivered_orders = [order for order in orders if order.status == "DELIVERED"]
    active_orders = [order for order in orders if order.status in ACTIVE_STATUSES]

    delivered_revenue = money_total(delivered_orders, "grand_total")
    delivered_count = len(delivered_orders)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_orders": len(orders),
        "new_orders": count_status(orders, "NEW"),
        "preparing_orders": count_status(orders, "PREPARING"),
        "on_the_way_orders": count_status(orders, "ON_THE_WAY"),
        "delivered_orders": delivered_count,
        "cancelled_orders": count_status(orders, "CANCELLED"),
        "active_orders": len(active_orders),
        "active_grand_total": money_total(active_orders, "grand_total"),
        "delivered_revenue": delivered_revenue,
        "delivered_subtotal": money_total(delivered_orders, "subtotal"),
        "delivered_delivery_fees": money_total(delivered_orders, "delivery_fee"),
        "average_delivered_order_total": (
            delivered_revenue / delivered_count if delivered_count else Decimal("0.00")
        ),
        "top_products": build_top_products(delivered_orders),
        "daily_totals": build_daily_totals(orders),
    }


def get_orders_for_report(
    db: Session,
    *,
    start_date: date | None,
    end_date: date | None,
) -> list[Order]:
    query = select(Order).options(selectinload(Order.items))

    if start_date is not None:
        query = query.where(Order.created_at >= datetime.combine(start_date, time.min))
    if end_date is not None:
        query = query.where(Order.created_at <= datetime.combine(end_date, time.max))

    return list(db.scalars(query.order_by(Order.created_at.desc(), Order.id.desc())))


def count_status(orders: list[Order], status: str) -> int:
    return sum(1 for order in orders if order.status == status)


def money_total(orders: list[Order], field_name: str) -> Decimal:
    return sum((getattr(order, field_name) for order in orders), Decimal("0.00"))


def build_top_products(orders: list[Order]) -> list[dict[str, object]]:
    totals: dict[int, dict[str, object]] = {}

    for order in orders:
        for item in order.items:
            product_total = totals.setdefault(
                item.product_id,
                {
                    "product_id": item.product_id,
                    "product_name": item.product_name_snapshot,
                    "quantity": 0,
                    "revenue": Decimal("0.00"),
                },
            )
            product_total["quantity"] = int(product_total["quantity"]) + item.quantity
            product_total["revenue"] = product_total["revenue"] + item.line_total

    return sorted(
        totals.values(),
        key=lambda item: (-int(item["quantity"]), str(item["product_name"])),
    )[:10]


def build_daily_totals(orders: list[Order]) -> list[dict[str, object]]:
    totals: dict[date, dict[str, object]] = {}

    for order in orders:
        day = order.created_at.date()
        day_total = totals.setdefault(
            day,
            {
                "day": day,
                "order_count": 0,
                "delivered_count": 0,
                "cancelled_count": 0,
                "revenue": Decimal("0.00"),
                "delivery_fees": Decimal("0.00"),
            },
        )
        day_total["order_count"] = int(day_total["order_count"]) + 1
        if order.status == "DELIVERED":
            day_total["delivered_count"] = int(day_total["delivered_count"]) + 1
            day_total["revenue"] = day_total["revenue"] + order.grand_total
            day_total["delivery_fees"] = day_total["delivery_fees"] + order.delivery_fee
        elif order.status == "CANCELLED":
            day_total["cancelled_count"] = int(day_total["cancelled_count"]) + 1

    return sorted(totals.values(), key=lambda item: item["day"], reverse=True)
