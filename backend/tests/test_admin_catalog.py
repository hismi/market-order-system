from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.services.users import create_user


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
)


def test_admin_can_create_category_and_product(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)

    category_response = client.post(
        "/api/admin/categories",
        headers=auth_headers(admin),
        json={
            "name": "Sut Urunleri",
            "description": "Sut, yogurt ve peynir.",
            "display_order": 15,
            "is_active": True,
        },
    )

    assert category_response.status_code == 201
    category = category_response.json()
    assert category["slug"] == "sut-urunleri"

    product_response = client.post(
        "/api/admin/products",
        headers=auth_headers(admin),
        json={
            "category_id": category["id"],
            "name": "Gunluk Sut 1 L",
            "description": "Pastorize gunluk sut.",
            "sku": "SUT-1L",
            "image_url": "https://example.com/sut.jpg",
            "price": "38.50",
            "stock_quantity": 25,
            "is_active": True,
        },
    )

    assert product_response.status_code == 201
    product = product_response.json()
    assert product["slug"] == "gunluk-sut-1-l"
    assert product["price"] == "38.50"
    assert product["stock_quantity"] == 25
    assert product["category"]["slug"] == "sut-urunleri"
    assert db_session.query(AuditLog).count() == 2


def test_admin_can_update_product_price_and_stock(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)
    category = Category(name="Icecek", slug="icecek", is_active=True)
    product = Product(
        category=category,
        name="Su 1.5 L",
        slug="su-15-l",
        price=Decimal("12.00"),
        stock_quantity=60,
        is_active=True,
    )
    db_session.add(product)
    db_session.commit()

    response = client.patch(
        f"/api/admin/products/{product.id}",
        headers=auth_headers(admin),
        json={
            "category_id": category.id,
            "name": "Su 1.5 L",
            "slug": "su-15-l",
            "description": "1.5 litre su.",
            "sku": None,
            "image_url": None,
            "price": "15.00",
            "stock_quantity": 42,
            "is_active": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["price"] == "15.00"
    assert data["stock_quantity"] == 42

    public_response = client.get("/api/catalog/products/su-15-l")
    assert public_response.status_code == 200
    assert public_response.json()["price"] == "15.00"


def test_admin_can_deactivate_product_and_hide_it_from_public_catalog(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)
    product = Product(
        name="Pasife Alinacak Urun",
        slug="pasife-alinacak-urun",
        price=Decimal("20.00"),
        stock_quantity=10,
        is_active=True,
    )
    db_session.add(product)
    db_session.commit()

    response = client.post(
        f"/api/admin/products/{product.id}/deactivate",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    public_response = client.get("/api/catalog/products/pasife-alinacak-urun")
    assert public_response.status_code == 404


def test_admin_can_upload_product_image(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)
    image_url = ""

    response = client.post(
        "/api/admin/products/images",
        headers=auth_headers(admin),
        files={"file": ("sut.png", PNG_BYTES, "image/png")},
    )

    try:
        assert response.status_code == 201
        image_url = response.json()["image_url"]
        assert image_url.startswith("/uploads/products/")
        assert image_url.endswith(".png")

        file_response = client.get(image_url)
        assert file_response.status_code == 200
        assert file_response.content.startswith(b"\x89PNG")

        audit_log = (
            db_session.query(AuditLog)
            .filter_by(action="PRODUCT_IMAGE_UPLOADED")
            .one()
        )
        assert audit_log.actor_username_snapshot == admin.username
    finally:
        if image_url:
            (Path("uploads") / "products" / Path(image_url).name).unlink(
                missing_ok=True,
            )


def test_product_image_upload_rejects_mismatched_content(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)

    response = client.post(
        "/api/admin/products/images",
        headers=auth_headers(admin),
        files={"file": ("not-image.png", b"not a png", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Dosya icerigi secilen gorsel tipiyle uyusmuyor."


def test_employee_cannot_access_admin_catalog_endpoints(
    client: TestClient,
    db_session: Session,
) -> None:
    employee = create_user(
        db_session,
        username="employee",
        password="Employee12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )

    response = client.get(
        "/api/admin/products",
        headers=auth_headers(employee),
    )

    assert response.status_code == 403

    upload_response = client.post(
        "/api/admin/products/images",
        headers=auth_headers(employee),
        files={"file": ("sut.png", PNG_BYTES, "image/png")},
    )

    assert upload_response.status_code == 403


def test_admin_product_rejects_duplicate_slug(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)
    db_session.add(
        Product(
            name="Elma 1 kg",
            slug="elma-1-kg",
            price=Decimal("65.00"),
            stock_quantity=10,
            is_active=True,
        )
    )
    db_session.commit()

    response = client.post(
        "/api/admin/products",
        headers=auth_headers(admin),
        json={
            "category_id": None,
            "name": "Elma 1 kg",
            "slug": "elma-1-kg",
            "description": None,
            "sku": None,
            "image_url": None,
            "price": "70.00",
            "stock_quantity": 5,
            "is_active": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Bu urun slug degeri zaten kullaniliyor."


def create_admin(db_session: Session) -> User:
    return create_user(
        db_session,
        username="admin",
        password="Admin12345",
        full_name="Admin",
        role="ADMIN",
    )


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )
    return {"Authorization": f"Bearer {token}"}
