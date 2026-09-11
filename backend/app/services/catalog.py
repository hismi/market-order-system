from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.category import Category
from app.models.product import Product


def seed_catalog_if_empty(db: Session) -> None:
    existing_category = db.scalar(select(Category.id).limit(1))
    if existing_category is not None:
        return

    fruit = Category(
        name="Meyve Sebze",
        slug="meyve-sebze",
        description="Gunluk taze meyve ve sebzeler.",
        display_order=10,
    )
    grocery = Category(
        name="Temel Gida",
        slug="temel-gida",
        description="Mutfak icin temel gida urunleri.",
        display_order=20,
    )
    drinks = Category(
        name="Icecek",
        slug="icecek",
        description="Su, soda ve gunluk icecekler.",
        display_order=30,
    )

    db.add_all([fruit, grocery, drinks])
    db.flush()

    db.add_all(
        [
            Product(
                category_id=fruit.id,
                name="Elma 1 kg",
                slug="elma-1-kg",
                description="Taze kirmizi elma.",
                image_url="https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?auto=format&fit=crop&w=800&q=80",
                price=Decimal("65.00"),
                stock_quantity=24,
            ),
            Product(
                category_id=fruit.id,
                name="Domates 1 kg",
                slug="domates-1-kg",
                description="Gunluk taze domates.",
                image_url="https://images.unsplash.com/photo-1546470427-e5ac89d5817e?auto=format&fit=crop&w=800&q=80",
                price=Decimal("48.50"),
                stock_quantity=18,
            ),
            Product(
                category_id=grocery.id,
                name="Pirinc 1 kg",
                slug="pirinc-1-kg",
                description="Pilavlik pirinc.",
                image_url="https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=800&q=80",
                price=Decimal("72.00"),
                stock_quantity=15,
            ),
            Product(
                category_id=drinks.id,
                name="Su 1.5 L",
                slug="su-15-l",
                description="1.5 litre pet sise su.",
                image_url="https://images.unsplash.com/photo-1564419320461-6870880221ad?auto=format&fit=crop&w=800&q=80",
                price=Decimal("12.00"),
                stock_quantity=60,
            ),
            Product(
                category_id=drinks.id,
                name="Soda 200 ml",
                slug="soda-200-ml",
                description="Sade maden suyu.",
                image_url="https://images.unsplash.com/photo-1523362628745-0c100150b504?auto=format&fit=crop&w=800&q=80",
                price=Decimal("10.00"),
                stock_quantity=0,
            ),
        ]
    )
    db.commit()


def list_active_categories(db: Session) -> list[Category]:
    return list(
        db.scalars(
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.display_order, Category.name)
        )
    )


def list_active_products(
    db: Session,
    *,
    category_slug: str | None = None,
    search: str | None = None,
) -> list[Product]:
    query: Select[tuple[Product]] = (
        select(Product)
        .options(selectinload(Product.category))
        .join(Category, Product.category_id == Category.id, isouter=True)
        .where(Product.is_active.is_(True))
        .where((Category.id.is_(None)) | (Category.is_active.is_(True)))
    )

    if category_slug:
        query = query.where(Category.slug == category_slug)

    if search:
        normalized_search = f"%{search.strip().lower()}%"
        query = query.where(func.lower(Product.name).like(normalized_search))

    return list(db.scalars(query.order_by(Product.name)))


def get_active_product_by_slug(db: Session, slug: str) -> Product | None:
    return db.scalar(
        select(Product)
        .options(selectinload(Product.category))
        .join(Category, Product.category_id == Category.id, isouter=True)
        .where(Product.slug == slug)
        .where(Product.is_active.is_(True))
        .where((Category.id.is_(None)) | (Category.is_active.is_(True)))
        .limit(1)
    )
