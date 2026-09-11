from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.schemas.admin_catalog import CategoryWrite, ProductWrite
from app.services.audit import write_audit_log
from app.services.slugs import slugify


def list_admin_categories(db: Session) -> list[Category]:
    return list(
        db.scalars(
            select(Category).order_by(
                Category.display_order,
                Category.name,
                Category.id,
            )
        )
    )


def create_category(db: Session, *, payload: CategoryWrite, actor: User) -> Category:
    slug = resolve_unique_category_slug(db, payload.slug or slugify(payload.name))
    category = Category(
        name=payload.name,
        slug=slug,
        description=payload.description,
        display_order=payload.display_order,
        is_active=payload.is_active,
    )
    db.add(category)
    db.flush()
    write_audit_log(
        db,
        actor=actor,
        action="CATEGORY_CREATED",
        target_type="categories",
        target_id=category.id,
        description=f"{actor.username} kategori olusturdu: {category.name}",
    )
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session,
    *,
    category_id: int,
    payload: CategoryWrite,
    actor: User,
) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise ValueError("Kategori bulunamadi.")

    slug = resolve_unique_category_slug(
        db,
        payload.slug or slugify(payload.name),
        current_id=category.id,
    )
    category.name = payload.name
    category.slug = slug
    category.description = payload.description
    category.display_order = payload.display_order
    category.is_active = payload.is_active
    write_audit_log(
        db,
        actor=actor,
        action="CATEGORY_UPDATED",
        target_type="categories",
        target_id=category.id,
        description=f"{actor.username} kategori guncelledi: {category.name}",
    )
    db.commit()
    db.refresh(category)
    return category


def list_admin_products(db: Session, *, search: str | None = None) -> list[Product]:
    query = select(Product).options(selectinload(Product.category))

    if search:
        normalized_search = f"%{search.strip().lower()}%"
        query = query.where(func.lower(Product.name).like(normalized_search))

    return list(db.scalars(query.order_by(Product.name, Product.id)))


def create_product(db: Session, *, payload: ProductWrite, actor: User) -> Product:
    validate_category_exists(db, payload.category_id)
    validate_unique_sku(db, payload.sku)
    slug = resolve_unique_product_slug(db, payload.slug or slugify(payload.name))
    product = Product(
        category_id=payload.category_id,
        name=payload.name,
        slug=slug,
        description=payload.description,
        sku=payload.sku,
        image_url=payload.image_url,
        price=payload.price,
        stock_quantity=payload.stock_quantity,
        is_active=payload.is_active,
    )
    db.add(product)
    db.flush()
    write_audit_log(
        db,
        actor=actor,
        action="PRODUCT_CREATED",
        target_type="products",
        target_id=product.id,
        description=f"{actor.username} urun olusturdu: {product.name}",
    )
    db.commit()
    return get_admin_product(db, product.id) or product


def update_product(
    db: Session,
    *,
    product_id: int,
    payload: ProductWrite,
    actor: User,
) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise ValueError("Urun bulunamadi.")

    validate_category_exists(db, payload.category_id)
    validate_unique_sku(db, payload.sku, current_id=product.id)
    slug = resolve_unique_product_slug(
        db,
        payload.slug or slugify(payload.name),
        current_id=product.id,
    )
    product.category_id = payload.category_id
    product.name = payload.name
    product.slug = slug
    product.description = payload.description
    product.sku = payload.sku
    product.image_url = payload.image_url
    product.price = payload.price
    product.stock_quantity = payload.stock_quantity
    product.is_active = payload.is_active
    write_audit_log(
        db,
        actor=actor,
        action="PRODUCT_UPDATED",
        target_type="products",
        target_id=product.id,
        description=f"{actor.username} urun guncelledi: {product.name}",
    )
    db.commit()
    return get_admin_product(db, product.id) or product


def deactivate_product(db: Session, *, product_id: int, actor: User) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise ValueError("Urun bulunamadi.")

    product.is_active = False
    write_audit_log(
        db,
        actor=actor,
        action="PRODUCT_DEACTIVATED",
        target_type="products",
        target_id=product.id,
        description=f"{actor.username} urunu pasife aldi: {product.name}",
    )
    db.commit()
    return get_admin_product(db, product.id) or product


def get_admin_product(db: Session, product_id: int) -> Product | None:
    return db.scalar(
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.id == product_id)
        .limit(1)
    )


def resolve_unique_category_slug(
    db: Session,
    slug: str,
    *,
    current_id: int | None = None,
) -> str:
    normalized_slug = slugify(slug)
    existing = db.scalar(select(Category).where(Category.slug == normalized_slug).limit(1))
    if existing is not None and existing.id != current_id:
        raise ValueError("Bu kategori slug degeri zaten kullaniliyor.")
    return normalized_slug


def resolve_unique_product_slug(
    db: Session,
    slug: str,
    *,
    current_id: int | None = None,
) -> str:
    normalized_slug = slugify(slug)
    existing = db.scalar(select(Product).where(Product.slug == normalized_slug).limit(1))
    if existing is not None and existing.id != current_id:
        raise ValueError("Bu urun slug degeri zaten kullaniliyor.")
    return normalized_slug


def validate_unique_sku(
    db: Session,
    sku: str | None,
    *,
    current_id: int | None = None,
) -> None:
    if sku is None:
        return

    existing = db.scalar(select(Product).where(Product.sku == sku).limit(1))
    if existing is not None and existing.id != current_id:
        raise ValueError("Bu SKU zaten kullaniliyor.")


def validate_category_exists(db: Session, category_id: int | None) -> None:
    if category_id is None:
        return

    if db.get(Category, category_id) is None:
        raise ValueError("Kategori bulunamadi.")
