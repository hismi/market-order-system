from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product


def test_public_categories_only_show_active_categories(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add_all(
        [
            Category(name="Icecek", slug="icecek", display_order=20, is_active=True),
            Category(
                name="Pasif Kategori",
                slug="pasif-kategori",
                display_order=10,
                is_active=False,
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/catalog/categories")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "name": "Icecek",
            "slug": "icecek",
            "description": None,
            "display_order": 20,
        }
    ]


def test_public_products_support_search_and_hide_inactive_products(
    client: TestClient,
    db_session: Session,
) -> None:
    category = Category(name="Meyve Sebze", slug="meyve-sebze", is_active=True)
    db_session.add(category)
    db_session.flush()
    db_session.add_all(
        [
            Product(
                category_id=category.id,
                name="Elma 1 kg",
                slug="elma-1-kg",
                price=Decimal("65.00"),
                stock_quantity=12,
                is_active=True,
            ),
            Product(
                category_id=category.id,
                name="Armut 1 kg",
                slug="armut-1-kg",
                price=Decimal("70.00"),
                stock_quantity=8,
                is_active=False,
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/catalog/products", params={"search": "elma"})

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Elma 1 kg"
    assert data[0]["price"] == "65.00"
    assert data[0]["is_in_stock"] is True
    assert data[0]["category"]["slug"] == "meyve-sebze"


def test_public_product_detail_returns_404_for_inactive_product(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add(
        Product(
            name="Gizli Urun",
            slug="gizli-urun",
            price=Decimal("25.00"),
            stock_quantity=5,
            is_active=False,
        )
    )
    db_session.commit()

    response = client.get("/api/catalog/products/gizli-urun")

    assert response.status_code == 404
