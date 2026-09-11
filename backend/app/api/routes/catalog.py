from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.category import Category
from app.models.product import Product
from app.schemas.catalog import CategoryRead, ProductRead
from app.services.catalog import (
    get_active_product_by_slug,
    list_active_categories,
    list_active_products,
)

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("/categories", response_model=list[CategoryRead])
def read_categories(db: Session = Depends(get_db)) -> list[Category]:
    return list_active_categories(db)


@router.get("/products", response_model=list[ProductRead])
def read_products(
    category: str | None = Query(default=None, min_length=1, max_length=140),
    search: str | None = Query(default=None, min_length=1, max_length=80),
    db: Session = Depends(get_db),
) -> list[Product]:
    return list_active_products(db, category_slug=category, search=search)


@router.get("/products/{slug}", response_model=ProductRead)
def read_product_detail(
    slug: str,
    db: Session = Depends(get_db),
) -> Product:
    product = get_active_product_by_slug(db, slug)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    return product
