from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.services.market_settings import get_market_settings


class PricingError(ValueError):
    pass


class MinimumOrderError(PricingError):
    def __init__(self, minimum: Decimal, subtotal: Decimal) -> None:
        self.minimum = minimum
        self.subtotal = subtotal
        self.remaining = minimum - subtotal
        super().__init__("Minimum siparis tutari saglanmadi.")


@dataclass(frozen=True)
class PricedCartItem:
    product: Product
    quantity: int
    line_total: Decimal


@dataclass(frozen=True)
class PricedCart:
    items: list[PricedCartItem]
    subtotal: Decimal
    delivery_fee: Decimal
    grand_total: Decimal


def calculate_cart_totals(
    db: Session,
    requested_items: list[tuple[int, int]],
) -> PricedCart:
    if not requested_items:
        raise PricingError("Sepet bos olamaz.")

    quantities_by_product_id: dict[int, int] = {}
    for product_id, quantity in requested_items:
        if quantity <= 0:
            raise PricingError("Urun adedi 1 veya daha buyuk olmalidir.")
        quantities_by_product_id[product_id] = (
            quantities_by_product_id.get(product_id, 0) + quantity
        )

    if any(quantity > 99 for quantity in quantities_by_product_id.values()):
        raise PricingError("Bir urun icin en fazla 99 adet siparis verilebilir.")

    products = list(
        db.scalars(
            select(Product)
            .where(Product.id.in_(quantities_by_product_id.keys()))
            .where(Product.is_active.is_(True))
        )
    )
    products_by_id = {product.id: product for product in products}

    missing_product_ids = set(quantities_by_product_id) - set(products_by_id)
    if missing_product_ids:
        raise PricingError("Sepette gecersiz veya pasif urun var.")

    priced_items: list[PricedCartItem] = []
    subtotal = Decimal("0.00")

    for product_id, quantity in quantities_by_product_id.items():
        product = products_by_id[product_id]
        if product.stock_quantity < quantity:
            raise PricingError(f"{product.name} icin yeterli stok yok.")

        line_total = product.price * quantity
        subtotal += line_total
        priced_items.append(
            PricedCartItem(
                product=product,
                quantity=quantity,
                line_total=line_total,
            )
        )

    settings = get_market_settings(db)
    if subtotal < settings.minimum_order_amount:
        raise MinimumOrderError(settings.minimum_order_amount, subtotal)

    delivery_fee = settings.delivery_fee
    grand_total = subtotal + delivery_fee

    return PricedCart(
        items=priced_items,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        grand_total=grand_total,
    )
