from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.audit_log import AuditLog
from app.models.delivery_area import DeliveryArea
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderCreate
from app.services.market_settings import get_market_settings
from app.services.orders import create_order
from app.services.users import create_user


def test_employee_orders_require_auth(client: TestClient) -> None:
    response = client.get("/api/employee/orders")

    assert response.status_code == 401


def test_customer_role_cannot_access_employee_orders(
    client: TestClient,
    db_session: Session,
) -> None:
    user = create_user(
        db_session,
        username="customer",
        password="Customer12345",
        full_name="Musteri",
        role="CUSTOMER",
    )

    response = client.get(
        "/api/employee/orders",
        headers=auth_headers(user),
    )

    assert response.status_code == 403


def test_employee_can_list_and_move_order_through_valid_statuses(
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
    order_id = create_sample_order(db_session).id

    list_response = client.get(
        "/api/employee/orders",
        headers=auth_headers(employee),
    )
    assert list_response.status_code == 200
    assert list_response.json()[0]["status"] == "NEW"

    approve_response = client.post(
        f"/api/employee/orders/{order_id}/approve",
        headers=auth_headers(employee),
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "PREPARING"
    product = db_session.query(Product).filter_by(slug="elma-1-kg").one()
    assert product.stock_quantity == 18

    on_the_way_response = client.post(
        f"/api/employee/orders/{order_id}/on-the-way",
        headers=auth_headers(employee),
    )
    assert on_the_way_response.status_code == 200
    assert on_the_way_response.json()["status"] == "ON_THE_WAY"

    delivered_response = client.post(
        f"/api/employee/orders/{order_id}/delivered",
        headers=auth_headers(employee),
    )
    assert delivered_response.status_code == 200
    assert delivered_response.json()["status"] == "DELIVERED"

    audit_count = db_session.query(AuditLog).count()
    assert audit_count == 3


def test_employee_cannot_skip_status_flow(
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
    order_id = create_sample_order(db_session).id

    response = client.post(
        f"/api/employee/orders/{order_id}/delivered",
        headers=auth_headers(employee),
    )

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Gecersiz siparis durum gecisi."


def test_employee_can_reject_new_order_with_reason(
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
    order_id = create_sample_order(db_session).id

    response = client.post(
        f"/api/employee/orders/{order_id}/reject",
        headers=auth_headers(employee),
        json={"reason": "BUSY"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["cancellation_reason"] == "Yogunluk"


def test_employee_can_cancel_preparing_order_and_restore_stock(
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
    order_id = create_sample_order(db_session).id

    approve_response = client.post(
        f"/api/employee/orders/{order_id}/approve",
        headers=auth_headers(employee),
    )
    assert approve_response.status_code == 200
    product = db_session.query(Product).filter_by(slug="elma-1-kg").one()
    assert product.stock_quantity == 18

    cancel_response = client.post(
        f"/api/employee/orders/{order_id}/reject",
        headers=auth_headers(employee),
        json={"reason": "CUSTOMER_UNREACHABLE"},
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "CANCELLED"
    db_session.refresh(product)
    assert product.stock_quantity == 20


def test_employee_cannot_approve_when_current_stock_is_not_enough(
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
    order_id = create_sample_order(db_session).id
    product = db_session.query(Product).filter_by(slug="elma-1-kg").one()
    product.stock_quantity = 1
    db_session.commit()

    response = client.post(
        f"/api/employee/orders/{order_id}/approve",
        headers=auth_headers(employee),
    )

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Elma 1 kg icin yeterli stok yok."
    db_session.refresh(product)
    order = db_session.get(Order, order_id)
    assert product.stock_quantity == 1
    assert order is not None
    assert order.status == "NEW"


def create_sample_order(db_session: Session):
    settings = get_market_settings(db_session)
    settings.minimum_order_amount = Decimal("10.00")
    settings.delivery_fee = Decimal("50.00")
    area = DeliveryArea(name="Merkez", slug="merkez", is_active=True)
    product = Product(
        name="Elma 1 kg",
        slug="elma-1-kg",
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
