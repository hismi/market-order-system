import secrets
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderCreate
from app.services.audit import write_audit_log
from app.services.delivery_areas import get_active_delivery_area
from app.services.market_settings import (
    OUTSIDE_WORKING_HOURS_REASON,
    get_market_acceptance_status,
    get_market_settings,
)
from app.services.pricing import PricingError, calculate_cart_totals

VALID_STATUSES = {"NEW", "PREPARING", "ON_THE_WAY", "DELIVERED", "CANCELLED"}
ORDER_NUMBER_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ORDER_NUMBER_RANDOM_LENGTH = 8
ORDER_NUMBER_MAX_ATTEMPTS = 20
STATUS_TRANSITIONS = {
    "NEW": {"PREPARING", "CANCELLED"},
    "PREPARING": {"ON_THE_WAY", "CANCELLED"},
    "ON_THE_WAY": {"DELIVERED", "CANCELLED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
}

CANCELLATION_REASONS = {
    "OUT_OF_STOCK": "Urun stokta yok",
    "OUT_OF_DELIVERY_AREA": "Teslimat bolgesi disinda",
    "BUSY": "Yogunluk",
    "CLOSING_SOON": "Market kapanmak uzere",
    "CUSTOMER_UNREACHABLE": "Musteriye ulasilamadi",
    "OTHER": "Diger",
}


def create_order(db: Session, payload: OrderCreate) -> Order:
    settings = get_market_settings(db)
    market_status = get_market_acceptance_status(settings)
    if not market_status.accepting_orders:
        if market_status.closed_reason == OUTSIDE_WORKING_HOURS_REASON:
            raise PricingError("Market calisma saatleri disinda siparis kabul etmiyor.")
        raise PricingError("Market su anda kapali.")

    delivery_area = get_active_delivery_area(db, payload.delivery_area_id)
    if delivery_area is None:
        raise PricingError("Gecersiz teslimat bolgesi.")

    priced_cart = calculate_cart_totals(
        db,
        [(item.product_id, item.quantity) for item in payload.items],
    )

    order = Order(
        order_number=generate_unique_order_number(db),
        status="NEW",
        customer_first_name=payload.customer_first_name,
        customer_last_name=payload.customer_last_name,
        phone=payload.phone,
        delivery_area_id=delivery_area.id,
        delivery_area_name_snapshot=delivery_area.name,
        neighborhood=payload.neighborhood,
        street=payload.street,
        apartment=payload.apartment,
        flat=payload.flat,
        address_line=payload.address_line,
        address_directions=payload.address_directions,
        order_note=payload.order_note,
        payment_method=payload.payment_method,
        unavailable_policy=payload.unavailable_policy,
        subtotal=priced_cart.subtotal,
        delivery_fee=priced_cart.delivery_fee,
        grand_total=priced_cart.grand_total,
    )
    db.add(order)
    db.flush()

    order.items = [
        OrderItem(
            product_id=item.product.id,
            product_name_snapshot=item.product.name,
            unit_price_snapshot=item.product.price,
            quantity=item.quantity,
            line_total=item.line_total,
        )
        for item in priced_cart.items
    ]

    db.commit()
    db.refresh(order)
    return order


def list_orders(
    db: Session,
    *,
    status: str | None = None,
    limit: int | None = None,
) -> list[Order]:
    query = (
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc(), Order.id.desc())
    )

    if status:
        if status not in VALID_STATUSES:
            raise PricingError("Gecersiz siparis durumu.")
        query = query.where(Order.status == status)

    if limit is not None:
        query = query.limit(limit)

    return list(db.scalars(query))


def get_order_summary(db: Session) -> dict[str, int | Decimal]:
    orders = list_orders(db)
    active_statuses = {"NEW", "PREPARING", "ON_THE_WAY"}

    def count(status: str) -> int:
        return sum(1 for order in orders if order.status == status)

    def money_total(statuses: set[str], field_name: str) -> Decimal:
        return sum(
            (getattr(order, field_name) for order in orders if order.status in statuses),
            Decimal("0.00"),
        )

    return {
        "total_orders": len(orders),
        "new_orders": count("NEW"),
        "preparing_orders": count("PREPARING"),
        "on_the_way_orders": count("ON_THE_WAY"),
        "delivered_orders": count("DELIVERED"),
        "cancelled_orders": count("CANCELLED"),
        "active_orders": sum(1 for order in orders if order.status in active_statuses),
        "active_grand_total": money_total(active_statuses, "grand_total"),
        "delivered_revenue": money_total({"DELIVERED"}, "grand_total"),
        "delivered_delivery_fees": money_total({"DELIVERED"}, "delivery_fee"),
    }


def get_order(db: Session, order_id: int) -> Order | None:
    return db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id)
        .limit(1)
    )


def get_order_for_tracking(
    db: Session,
    *,
    order_number: str,
    phone: str,
) -> Order | None:
    normalized_order_number = normalize_order_number(order_number)
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_number == normalized_order_number)
        .limit(1)
    )

    if order is None or not phones_match(order.phone, phone):
        return None

    return order


def build_public_tracking_response(order: Order) -> dict[str, object]:
    return {
        "order_number": order.order_number,
        "status": order.status,
        "customer_name": mask_person_name(
            order.customer_first_name,
            order.customer_last_name,
        ),
        "phone": mask_phone_number(order.phone),
        "delivery_area": mask_words(order.delivery_area_name_snapshot),
        "payment_method": order.payment_method,
        "unavailable_policy": order.unavailable_policy,
        "cancellation_reason": order.cancellation_reason,
        "subtotal": order.subtotal,
        "delivery_fee": order.delivery_fee,
        "grand_total": order.grand_total,
        "created_at": order.created_at,
        "items": order.items,
    }


def change_order_status(
    db: Session,
    *,
    order_id: int,
    next_status: str,
    actor: User,
    cancellation_reason: str | None = None,
) -> Order:
    order = get_order(db, order_id)
    if order is None:
        raise PricingError("Siparis bulunamadi.")

    if next_status not in VALID_STATUSES:
        raise PricingError("Gecersiz siparis durumu.")

    if next_status not in STATUS_TRANSITIONS[order.status]:
        raise PricingError("Gecersiz siparis durum gecisi.")

    old_status = order.status

    if next_status == "PREPARING" and old_status == "NEW":
        decrease_stock_for_order(db, order)

    if next_status == "CANCELLED":
        if cancellation_reason not in CANCELLATION_REASONS:
            raise PricingError("Gecersiz iptal sebebi.")
        order.cancellation_reason = CANCELLATION_REASONS[cancellation_reason]
        if old_status in {"PREPARING", "ON_THE_WAY"}:
            restore_stock_for_order(db, order)

    order.status = next_status
    write_audit_log(
        db,
        actor=actor,
        action="ORDER_STATUS_CHANGED",
        target_type="orders",
        target_id=order.id,
        description=(
            f"{actor.username} siparis {order.order_number} durumunu "
            f"{old_status} -> {next_status} olarak degistirdi."
        ),
    )
    db.commit()
    db.refresh(order)
    return get_order(db, order.id) or order


def decrease_stock_for_order(db: Session, order: Order) -> None:
    stock_updates: list[tuple[Product, int, str]] = []

    for item in order.items:
        product = get_product_for_stock_update(db, item.product_id)
        if product is None:
            raise PricingError(f"{item.product_name_snapshot} urunu bulunamadi.")
        if product.stock_quantity < item.quantity:
            raise PricingError(
                f"{item.product_name_snapshot} icin yeterli stok yok."
            )
        stock_updates.append((product, item.quantity, item.product_name_snapshot))

    for product, quantity, _ in stock_updates:
        product.stock_quantity -= quantity


def restore_stock_for_order(db: Session, order: Order) -> None:
    for item in order.items:
        product = get_product_for_stock_update(db, item.product_id)
        if product is not None:
            product.stock_quantity += item.quantity


def get_product_for_stock_update(db: Session, product_id: int) -> Product | None:
    return db.scalar(select(Product).where(Product.id == product_id).limit(1))


def generate_unique_order_number(db: Session) -> str:
    for _ in range(ORDER_NUMBER_MAX_ATTEMPTS):
        order_number = generate_order_number()
        if not order_number_exists(db, order_number):
            return order_number

    raise PricingError("Siparis numarasi olusturulamadi. Lutfen tekrar deneyin.")


def generate_order_number() -> str:
    code = "".join(
        secrets.choice(ORDER_NUMBER_ALPHABET)
        for _ in range(ORDER_NUMBER_RANDOM_LENGTH)
    )
    return f"MKT-{code[:4]}-{code[4:]}"


def order_number_exists(db: Session, order_number: str) -> bool:
    return db.scalar(
        select(Order.id).where(Order.order_number == order_number).limit(1)
    ) is not None


def normalize_order_number(value: str) -> str:
    text = value.strip().upper().replace(" ", "")
    if text and not text.startswith("#") and text.isdigit():
        return f"#{text}"
    compact_text = text.replace("-", "")
    if compact_text.startswith("MKT") and len(compact_text) == 11:
        code = compact_text[3:]
        if all(char in ORDER_NUMBER_ALPHABET for char in code):
            return f"MKT-{code[:4]}-{code[4:]}"
    return text


def phones_match(saved_phone: str, submitted_phone: str) -> bool:
    saved_digits = only_digits(saved_phone)
    submitted_digits = only_digits(submitted_phone)
    return (
        len(saved_digits) >= 10
        and len(submitted_digits) >= 10
        and saved_digits[-10:] == submitted_digits[-10:]
    )


def only_digits(value: str) -> str:
    return "".join(char for char in value if char.isdigit())


def mask_person_name(first_name: str, last_name: str) -> str:
    return mask_words(f"{first_name} {last_name}")


def mask_words(value: str) -> str:
    return " ".join(mask_word(word) for word in value.split())


def mask_word(value: str) -> str:
    if not value:
        return ""

    if len(value) <= 2:
        return f"{value[0]}*"

    return f"{value[:2]}{'*' * (len(value) - 2)}"


def mask_phone_number(value: str) -> str:
    digits = normalize_phone_digits_for_display(only_digits(value))
    if len(digits) < 4:
        return "**"

    return f"{digits[:2]}** *** ** {digits[-2:]}"


def normalize_phone_digits_for_display(digits: str) -> str:
    if digits.startswith("90") and len(digits) == 12:
        return f"0{digits[2:]}"

    if digits.startswith("5") and len(digits) == 10:
        return f"0{digits}"

    if len(digits) > 11:
        return digits[-11:]

    return digits
