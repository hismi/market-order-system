from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.users import create_user


def test_public_market_settings_has_server_owned_order_rules(
    client: TestClient,
) -> None:
    response = client.get("/api/market-settings/public")

    assert response.status_code == 200
    assert response.json()["minimum_order_amount"] == "300.00"
    assert response.json()["delivery_fee"] == "50.00"


def test_admin_can_update_market_settings(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_user(
        db_session,
        username="admin",
        password="Admin12345",
        full_name="Admin",
        role="ADMIN",
    )

    response = client.patch(
        "/api/market-settings/admin",
        headers=auth_headers(admin),
        json={
            "market_name": "Mahalle Market",
            "phone": "0532 111 22 33",
            "whatsapp_number": "0532 111 22 33",
            "is_open": True,
            "opening_time": "08:30:00",
            "closing_time": "22:00:00",
            "minimum_order_amount": "400.00",
            "delivery_fee": "75.00",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["market_name"] == "Mahalle Market"
    assert data["minimum_order_amount"] == "400.00"
    assert data["delivery_fee"] == "75.00"
    assert db_session.query(AuditLog).count() == 1

    public_response = client.get("/api/market-settings/public")
    assert public_response.status_code == 200
    assert public_response.json()["delivery_fee"] == "75.00"


def test_employee_cannot_update_market_settings(
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

    response = client.patch(
        "/api/market-settings/admin",
        headers=auth_headers(employee),
        json={
            "market_name": "Mahalle Market",
            "phone": None,
            "whatsapp_number": None,
            "is_open": True,
            "opening_time": None,
            "closing_time": None,
            "minimum_order_amount": "400.00",
            "delivery_fee": "75.00",
        },
    )

    assert response.status_code == 403


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )
    return {"Authorization": f"Bearer {token}"}
