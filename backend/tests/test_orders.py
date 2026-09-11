import re
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.delivery_area import DeliveryArea
from app.models.order import Order
from app.models.product import Product
from app.services.market_settings import get_market_settings


def test_create_order_recalculates_totals_and_ignores_frontend_money_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    settings = get_market_settings(db_session)
    settings.minimum_order_amount = Decimal("100.00")
    settings.delivery_fee = Decimal("50.00")
    area = DeliveryArea(
        name="Merkez Mahallesi",
        slug="merkez-mahallesi",
        is_active=True,
    )
    product = Product(
        name="Elma 1 kg",
        slug="elma-1-kg",
        price=Decimal("100.00"),
        stock_quantity=8,
        is_active=True,
    )
    db_session.add_all([area, product])
    db_session.commit()

    response = client.post(
        "/api/orders",
        json={
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 2,
                    "price": "1.00",
                }
            ],
            "customer_first_name": "Sait",
            "customer_last_name": "Hismi",
            "phone": "0532 111 22 33",
            "delivery_area_id": area.id,
            "neighborhood": "Merkez Mahallesi",
            "street": "Market Sokak",
            "apartment": "A Blok",
            "flat": "4",
            "address_line": "Merkez Mahallesi Market Sokak No 10",
            "address_directions": "Kapi zili calismiyor.",
            "order_note": "Domates sert olsun.",
            "payment_method": "CARD_ON_DELIVERY",
            "unavailable_policy": "CALL_CUSTOMER",
            "subtotal": "1.00",
            "delivery_fee": "0.00",
            "grand_total": "1.00",
            "status": "DELIVERED",
            "role": "ADMIN",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" not in data
    assert re.fullmatch(
        r"MKT-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}",
        data["order_number"],
    )
    assert data["order_number"] != "#1001"
    assert data["status"] == "NEW"
    assert data["subtotal"] == "200.00"
    assert data["delivery_fee"] == "50.00"
    assert data["grand_total"] == "250.00"
    assert "product_id" not in data["items"][0]
    assert data["items"][0]["unit_price_snapshot"] == "100.00"
    assert data["items"][0]["line_total"] == "200.00"

    order = db_session.query(Order).filter_by(order_number=data["order_number"]).one()
    assert order.delivery_area_name_snapshot == "Merkez Mahallesi"
    assert order.items[0].product_name_snapshot == "Elma 1 kg"

    tracking_response = client.get(
        "/api/orders/track",
        params={
            "order_number": data["order_number"].lower().replace("-", ""),
            "phone": "+90 532 111 22 33",
        },
    )
    assert tracking_response.status_code == 200
    tracking_data = tracking_response.json()
    forbidden_keys = {
        "id",
        "customer_first_name",
        "customer_last_name",
        "delivery_area_name_snapshot",
        "neighborhood",
        "street",
        "apartment",
        "flat",
        "address_line",
        "address_directions",
        "order_note",
        "updated_at",
        "tracking_token",
    }
    assert tracking_data["order_number"] == data["order_number"]
    assert tracking_data["status"] == "NEW"
    assert tracking_data["customer_name"] == "Sa** Hi***"
    assert tracking_data["phone"] == "05** *** ** 33"
    assert tracking_data["delivery_area"] == "Me**** Ma*******"
    assert tracking_data["delivery_fee"] == "50.00"
    assert not forbidden_keys.intersection(tracking_data.keys())
    assert "product_id" not in tracking_data["items"][0]

    raw_tracking_response = tracking_response.text
    assert "Sait" not in raw_tracking_response
    assert "Hismi" not in raw_tracking_response
    assert "0532" not in raw_tracking_response
    assert "111 22" not in raw_tracking_response
    assert "Market Sokak" not in raw_tracking_response
    assert "A Blok" not in raw_tracking_response
    assert "Kapi zili" not in raw_tracking_response
    assert "Domates" not in raw_tracking_response


def test_track_order_rejects_wrong_phone(
    client: TestClient,
    db_session: Session,
) -> None:
    settings = get_market_settings(db_session)
    settings.minimum_order_amount = Decimal("10.00")
    settings.delivery_fee = Decimal("50.00")
    area = DeliveryArea(name="Merkez", slug="merkez", is_active=True)
    product = Product(
        name="Elma 1 kg",
        slug="elma-1-kg",
        price=Decimal("100.00"),
        stock_quantity=8,
        is_active=True,
    )
    db_session.add_all([area, product])
    db_session.commit()

    create_response = client.post(
        "/api/orders",
        json={
            "items": [{"product_id": product.id, "quantity": 1}],
            "customer_first_name": "Sait",
            "customer_last_name": "Musteri",
            "phone": "0532 111 22 33",
            "delivery_area_id": area.id,
            "neighborhood": "Merkez Mahallesi",
            "street": "Market Sokak",
            "address_line": "Merkez Mahallesi Market Sokak No 10",
            "payment_method": "CASH_ON_DELIVERY",
            "unavailable_policy": "CALL_CUSTOMER",
        },
    )
    assert create_response.status_code == 201

    tracking_response = client.get(
        "/api/orders/track",
        params={
            "order_number": create_response.json()["order_number"],
            "phone": "0532 999 99 99",
        },
    )

    assert tracking_response.status_code == 404
    assert tracking_response.json()["detail"]["code"] == "ORDER_NOT_FOUND"


def test_track_order_accepts_legacy_numeric_order_number(
    client: TestClient,
    db_session: Session,
) -> None:
    area = DeliveryArea(name="Merkez", slug="merkez", is_active=True)
    order = Order(
        order_number="#1001",
        status="NEW",
        customer_first_name="Sait",
        customer_last_name="Musteri",
        phone="0532 111 22 33",
        delivery_area_id=1,
        delivery_area_name_snapshot="Merkez",
        neighborhood="Merkez Mahallesi",
        street="Market Sokak",
        address_line="Merkez Mahallesi Market Sokak No 10",
        payment_method="CASH_ON_DELIVERY",
        unavailable_policy="CALL_CUSTOMER",
        subtotal=Decimal("100.00"),
        delivery_fee=Decimal("50.00"),
        grand_total=Decimal("150.00"),
    )
    db_session.add(area)
    db_session.flush()
    order.delivery_area_id = area.id
    db_session.add(order)
    db_session.commit()

    response = client.get(
        "/api/orders/track",
        params={
            "order_number": "1001",
            "phone": "0532 111 22 33",
        },
    )

    assert response.status_code == 200
    assert response.json()["order_number"] == "#1001"


def test_create_order_rejects_minimum_order_not_met(
    client: TestClient,
    db_session: Session,
) -> None:
    settings = get_market_settings(db_session)
    settings.minimum_order_amount = Decimal("300.00")
    settings.delivery_fee = Decimal("50.00")
    area = DeliveryArea(name="Merkez", slug="merkez", is_active=True)
    product = Product(
        name="Su 1.5 L",
        slug="su-15-l",
        price=Decimal("20.00"),
        stock_quantity=30,
        is_active=True,
    )
    db_session.add_all([area, product])
    db_session.commit()

    response = client.post(
        "/api/orders",
        json={
            "items": [{"product_id": product.id, "quantity": 10}],
            "customer_first_name": "Sait",
            "customer_last_name": "Musteri",
            "phone": "0532 111 22 33",
            "delivery_area_id": area.id,
            "neighborhood": "Merkez Mahallesi",
            "street": "Market Sokak",
            "address_line": "Merkez Mahallesi Market Sokak No 10",
            "payment_method": "CASH_ON_DELIVERY",
            "unavailable_policy": "REMOVE_ITEM",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == {
        "code": "MINIMUM_ORDER_NOT_MET",
        "message": "Minimum siparis tutari saglanmadi.",
        "minimum_order_amount": "300.00",
        "subtotal": "200.00",
        "remaining": "100.00",
    }


def test_create_order_rejects_out_of_stock_product(
    client: TestClient,
    db_session: Session,
) -> None:
    settings = get_market_settings(db_session)
    settings.minimum_order_amount = Decimal("10.00")
    area = DeliveryArea(name="Merkez", slug="merkez", is_active=True)
    product = Product(
        name="Soda 200 ml",
        slug="soda-200-ml",
        price=Decimal("10.00"),
        stock_quantity=0,
        is_active=True,
    )
    db_session.add_all([area, product])
    db_session.commit()

    response = client.post(
        "/api/orders",
        json={
            "items": [{"product_id": product.id, "quantity": 1}],
            "customer_first_name": "Sait",
            "customer_last_name": "Musteri",
            "phone": "0532 111 22 33",
            "delivery_area_id": area.id,
            "neighborhood": "Merkez Mahallesi",
            "street": "Market Sokak",
            "address_line": "Merkez Mahallesi Market Sokak No 10",
            "payment_method": "CASH_ON_DELIVERY",
            "unavailable_policy": "REMOVE_ITEM",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "ORDER_REJECTED"


def test_create_order_rejects_inactive_delivery_area(
    client: TestClient,
    db_session: Session,
) -> None:
    settings = get_market_settings(db_session)
    settings.minimum_order_amount = Decimal("10.00")
    area = DeliveryArea(name="Pasif Bolge", slug="pasif-bolge", is_active=False)
    product = Product(
        name="Ekmek",
        slug="ekmek",
        price=Decimal("12.00"),
        stock_quantity=20,
        is_active=True,
    )
    db_session.add_all([area, product])
    db_session.commit()

    response = client.post(
        "/api/orders",
        json={
            "items": [{"product_id": product.id, "quantity": 1}],
            "customer_first_name": "Sait",
            "customer_last_name": "Musteri",
            "phone": "0532 111 22 33",
            "delivery_area_id": area.id,
            "neighborhood": "Merkez Mahallesi",
            "street": "Market Sokak",
            "address_line": "Merkez Mahallesi Market Sokak No 10",
            "payment_method": "CASH_ON_DELIVERY",
            "unavailable_policy": "REMOVE_ITEM",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == {
        "code": "ORDER_REJECTED",
        "message": "Gecersiz teslimat bolgesi.",
    }
