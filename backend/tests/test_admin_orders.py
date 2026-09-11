from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.delivery_area import DeliveryArea
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderCreate
from app.services.market_settings import get_market_settings
from app.services.orders import change_order_status, create_order
from app.services.users import create_user


def test_admin_orders_require_admin_role(
    client: TestClient,
    db_session: Session,
) -> None:
    response_without_auth = client.get("/api/admin/orders")
    assert response_without_auth.status_code == 401

    employee = create_user(
        db_session,
        username="employee",
        password="Employee12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )

    response_with_employee = client.get(
        "/api/admin/orders",
        headers=auth_headers(employee),
    )
    assert response_with_employee.status_code == 403


def test_admin_can_list_and_filter_orders(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_user(
        db_session,
        username="admin",
        password="Admin12345",
        full_name="Market Sahibi",
        role="ADMIN",
    )
    create_sample_order(db_session, suffix="bir")
    preparing_order = create_sample_order(db_session, suffix="iki")
    change_order_status(
        db_session,
        order_id=preparing_order.id,
        next_status="PREPARING",
        actor=admin,
    )

    all_response = client.get(
        "/api/admin/orders",
        headers=auth_headers(admin),
    )
    assert all_response.status_code == 200
    assert len(all_response.json()) == 2

    filtered_response = client.get(
        "/api/admin/orders",
        headers=auth_headers(admin),
        params={"status": "PREPARING"},
    )
    assert filtered_response.status_code == 200
    filtered_orders = filtered_response.json()
    assert len(filtered_orders) == 1
    assert filtered_orders[0]["status"] == "PREPARING"


def test_admin_order_summary_counts_money_totals(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_user(
        db_session,
        username="admin",
        password="Admin12345",
        full_name="Market Sahibi",
        role="ADMIN",
    )
    create_sample_order(db_session, suffix="bir")
    delivered_order = create_sample_order(db_session, suffix="iki")
    change_order_status(
        db_session,
        order_id=delivered_order.id,
        next_status="PREPARING",
        actor=admin,
    )
    change_order_status(
        db_session,
        order_id=delivered_order.id,
        next_status="ON_THE_WAY",
        actor=admin,
    )
    change_order_status(
        db_session,
        order_id=delivered_order.id,
        next_status="DELIVERED",
        actor=admin,
    )

    response = client.get(
        "/api/admin/orders/summary",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_orders"] == 2
    assert data["new_orders"] == 1
    assert data["active_orders"] == 1
    assert data["delivered_orders"] == 1
    assert data["delivered_revenue"] == "180.00"
    assert data["delivered_delivery_fees"] == "50.00"
    assert data["active_grand_total"] == "180.00"


def create_sample_order(db_session: Session, *, suffix: str):
    settings = get_market_settings(db_session)
    settings.minimum_order_amount = Decimal("10.00")
    settings.delivery_fee = Decimal("50.00")
    area = DeliveryArea(name=f"Merkez {suffix}", slug=f"merkez-{suffix}", is_active=True)
    product = Product(
        name=f"Elma {suffix} 1 kg",
        slug=f"elma-{suffix}-1-kg",
        price=Decimal("65.00"),
        stock_quantity=20,
        is_active=True,
    )
    db_session.add_all([area, product])
    db_session.commit()

    return create_order(
        db_session,
        OrderCreate(
            items=[{"product_id": product.id, "quantity": 2}],
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


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )
    return {"Authorization": f"Bearer {token}"}
