from datetime import datetime, time, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import create_access_token
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.market_settings import get_market_acceptance_status
from app.services.users import create_user


def test_public_market_settings_has_server_owned_order_rules(
    client: TestClient,
) -> None:
    response = client.get("/api/market-settings/public")

    assert response.status_code == 200
    data = response.json()
    assert data["minimum_order_amount"] == "300.00"
    assert data["delivery_fee"] == "50.00"
    assert data["accepting_orders"] is True
    assert data["closed_reason"] is None
    assert data["timezone"] == "Europe/Istanbul"


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
    public_data = public_response.json()
    assert public_data["delivery_fee"] == "75.00"
    assert public_data["accepting_orders"] is not None


def test_market_acceptance_respects_working_hours(
    db_session: Session,
) -> None:
    from app.services.market_settings import get_market_settings

    settings = get_market_settings(db_session)
    settings.is_open = True
    settings.opening_time = time(9, 0)
    settings.closing_time = time(17, 0)

    app_settings = Settings(app_timezone="UTC")
    open_status = get_market_acceptance_status(
        settings,
        app_settings=app_settings,
        now=datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc),
    )
    closed_status = get_market_acceptance_status(
        settings,
        app_settings=app_settings,
        now=datetime(2026, 9, 11, 18, 0, tzinfo=timezone.utc),
    )

    assert open_status.accepting_orders is True
    assert open_status.closed_reason is None
    assert closed_status.accepting_orders is False
    assert closed_status.closed_reason == "OUTSIDE_WORKING_HOURS"


def test_market_acceptance_supports_overnight_working_hours(
    db_session: Session,
) -> None:
    from app.services.market_settings import get_market_settings

    settings = get_market_settings(db_session)
    settings.is_open = True
    settings.opening_time = time(20, 0)
    settings.closing_time = time(6, 0)

    app_settings = Settings(app_timezone="UTC")
    late_status = get_market_acceptance_status(
        settings,
        app_settings=app_settings,
        now=datetime(2026, 9, 11, 23, 0, tzinfo=timezone.utc),
    )
    noon_status = get_market_acceptance_status(
        settings,
        app_settings=app_settings,
        now=datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc),
    )

    assert late_status.accepting_orders is True
    assert noon_status.accepting_orders is False
    assert noon_status.closed_reason == "OUTSIDE_WORKING_HOURS"


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
