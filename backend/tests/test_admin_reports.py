from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.delivery_area import DeliveryArea
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderCreate
from app.services.market_settings import get_market_settings
from app.services.orders import change_order_status, create_order
from app.services.users import create_user


def test_admin_reports_require_admin_role(
    client: TestClient,
    db_session: Session,
) -> None:
    response_without_auth = client.get("/api/admin/reports/orders")
    assert response_without_auth.status_code == 401

    employee = create_user(
        db_session,
        username="employee",
        password="Employee12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )

    response_with_employee = client.get(
        "/api/admin/reports/orders",
        headers=auth_headers(employee),
    )
    assert response_with_employee.status_code == 403


def test_admin_order_report_summarizes_date_range_and_top_products(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)
    area, apple, water = seed_report_data(db_session)

    delivered_first = create_sample_order(db_session, area=area, product=apple, quantity=2)
    mark_delivered(db_session, delivered_first, admin)
    delivered_first.created_at = datetime(2026, 9, 1, 10, 0, 0)

    delivered_second = create_sample_order(db_session, area=area, product=apple, quantity=1)
    mark_delivered(db_session, delivered_second, admin)
    delivered_second.created_at = datetime(2026, 9, 2, 11, 0, 0)

    cancelled_order = create_sample_order(db_session, area=area, product=water, quantity=1)
    change_order_status(
        db_session,
        order_id=cancelled_order.id,
        next_status="CANCELLED",
        actor=admin,
        cancellation_reason="BUSY",
    )
    cancelled_order.created_at = datetime(2026, 9, 2, 12, 0, 0)

    active_order = create_sample_order(db_session, area=area, product=water, quantity=1)
    active_order.created_at = datetime(2026, 9, 3, 13, 0, 0)
    db_session.commit()

    response = client.get(
        "/api/admin/reports/orders",
        headers=auth_headers(admin),
        params={
            "start_date": "2026-09-01",
            "end_date": "2026-09-02",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["start_date"] == "2026-09-01"
    assert data["end_date"] == "2026-09-02"
    assert data["total_orders"] == 3
    assert data["delivered_orders"] == 2
    assert data["cancelled_orders"] == 1
    assert data["active_orders"] == 0
    assert data["delivered_subtotal"] == "195.00"
    assert data["delivered_delivery_fees"] == "100.00"
    assert data["delivered_revenue"] == "295.00"
    assert data["average_delivered_order_total"] == "147.50"
    assert data["top_products"][0] == {
        "product_id": apple.id,
        "product_name": "Elma 1 kg",
        "quantity": 3,
        "revenue": "195.00",
    }
    assert data["daily_totals"][0]["day"] == "2026-09-02"
    assert data["daily_totals"][0]["order_count"] == 2
    assert data["daily_totals"][0]["delivered_count"] == 1
    assert data["daily_totals"][0]["cancelled_count"] == 1


def test_admin_order_report_rejects_invalid_date_range(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)

    response = client.get(
        "/api/admin/reports/orders",
        headers=auth_headers(admin),
        params={
            "start_date": "2026-09-03",
            "end_date": "2026-09-01",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == (
        "Baslangic tarihi bitis tarihinden sonra olamaz."
    )


def seed_report_data(db_session: Session) -> tuple[DeliveryArea, Product, Product]:
    settings = get_market_settings(db_session)
    settings.minimum_order_amount = Decimal("10.00")
    settings.delivery_fee = Decimal("50.00")
    area = DeliveryArea(name="Merkez", slug="merkez", is_active=True)
    apple = Product(
        name="Elma 1 kg",
        slug="elma-1-kg",
        price=Decimal("65.00"),
        stock_quantity=20,
        is_active=True,
    )
    water = Product(
        name="Su 1.5 L",
        slug="su-15-l",
        price=Decimal("20.00"),
        stock_quantity=20,
        is_active=True,
    )
    db_session.add_all([area, apple, water])
    db_session.commit()
    return area, apple, water


def create_sample_order(
    db_session: Session,
    *,
    area: DeliveryArea,
    product: Product,
    quantity: int,
) -> Order:
    return create_order(
        db_session,
        OrderCreate(
            items=[{"product_id": product.id, "quantity": quantity}],
            customer_first_name="Sait",
            customer_last_name="Musteri",
            phone="0532 111 22 33",
            delivery_area_id=area.id,
            neighborhood="Merkez Mahallesi",
            street="Market Sokak",
            address_line="Merkez Mahallesi Market Sokak No 10",
            payment_method="CASH_ON_DELIVERY",
            unavailable_policy="CALL_CUSTOMER",
        ),
    )


def mark_delivered(db_session: Session, order: Order, admin: User) -> None:
    change_order_status(
        db_session,
        order_id=order.id,
        next_status="PREPARING",
        actor=admin,
    )
    change_order_status(
        db_session,
        order_id=order.id,
        next_status="ON_THE_WAY",
        actor=admin,
    )
    change_order_status(
        db_session,
        order_id=order.id,
        next_status="DELIVERED",
        actor=admin,
    )


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
