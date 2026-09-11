from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.schemas.admin_catalog import (
    AdminCategoryRead,
    AdminProductRead,
    CategoryWrite,
    ProductImageUploadRead,
    ProductWrite,
)
from app.services.admin_catalog import (
    create_category,
    create_product,
    deactivate_product,
    list_admin_categories,
    list_admin_products,
    update_category,
    update_product,
)
from app.services.audit import write_audit_log
from app.services.image_uploads import save_product_image

router = APIRouter(prefix="/api/admin", tags=["admin-catalog"])


@router.get("/categories", response_model=list[AdminCategoryRead])
def read_admin_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> list[Category]:
    _ = current_user
    return list_admin_categories(db)


@router.post(
    "/categories",
    response_model=AdminCategoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_category(
    payload: CategoryWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> Category:
    try:
        return create_category(db, payload=payload, actor=current_user)
    except ValueError as error:
        raise bad_request(error) from error


@router.patch("/categories/{category_id}", response_model=AdminCategoryRead)
def update_admin_category(
    category_id: int,
    payload: CategoryWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> Category:
    try:
        return update_category(
            db,
            category_id=category_id,
            payload=payload,
            actor=current_user,
        )
    except ValueError as error:
        raise bad_request(error) from error


@router.get("/products", response_model=list[AdminProductRead])
def read_admin_products(
    search: str | None = Query(default=None, min_length=1, max_length=80),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> list[Product]:
    _ = current_user
    return list_admin_products(db, search=search)


@router.post(
    "/products",
    response_model=AdminProductRead,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_product(
    payload: ProductWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> Product:
    try:
        return create_product(db, payload=payload, actor=current_user)
    except ValueError as error:
        raise bad_request(error) from error


@router.post(
    "/products/images",
    response_model=ProductImageUploadRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_admin_product_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
    settings: Settings = Depends(get_settings),
) -> ProductImageUploadRead:
    try:
        image_url = save_product_image(
            upload=file,
            upload_dir=Path(settings.upload_directory) / "products",
            max_bytes=settings.max_product_image_bytes,
        )
    except ValueError as error:
        raise bad_request(error) from error

    write_audit_log(
        db,
        actor=current_user,
        action="PRODUCT_IMAGE_UPLOADED",
        target_type="product_images",
        target_id=None,
        description=f"{current_user.username} urun gorseli yukledi.",
    )
    db.commit()
    return ProductImageUploadRead(image_url=image_url)


@router.patch("/products/{product_id}", response_model=AdminProductRead)
def update_admin_product(
    product_id: int,
    payload: ProductWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> Product:
    try:
        return update_product(
            db,
            product_id=product_id,
            payload=payload,
            actor=current_user,
        )
    except ValueError as error:
        raise bad_request(error) from error


@router.post("/products/{product_id}/deactivate", response_model=AdminProductRead)
def deactivate_admin_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> Product:
    try:
        return deactivate_product(db, product_id=product_id, actor=current_user)
    except ValueError as error:
        raise bad_request(error) from error


def bad_request(error: ValueError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": "ADMIN_CATALOG_REJECTED",
            "message": str(error),
        },
    )
