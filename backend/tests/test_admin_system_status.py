from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.delivery_area import DeliveryArea
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.services.market_settings import get_market_settings
from app.services.users import create_user


def test_admin_system_status_requires_admin_role(
    client: TestClient,
    db_session: Session,
) -> None:
    response_without_auth = client.get("/api/admin/system-status")
    assert response_without_auth.status_code == 401

    employee = create_user(
        db_session,
        username="employee",
        password="Employee12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )

    response_with_employee = client.get(
        "/api/admin/system-status",
        headers=auth_headers(employee),
    )
    assert response_with_employee.status_code == 403


def test_admin_system_status_returns_operational_summary(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)
    create_user(
        db_session,
        username="employee",
        password="Employee12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )
    seed_status_data(db_session, admin=admin)

    response = client.get(
        "/api/admin/system-status",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["api_status"] == "OK"
    assert data["market_name"] == "Test Market"
    assert data["market_is_open"] is True
    assert data["market_accepting_orders"] is True
    assert data["market_closed_reason"] is None
    assert data["market_timezone"] == "Europe/Istanbul"
    assert data["minimum_order_amount"] == "250.00"
    assert data["delivery_fee"] == "65.00"
    assert data["delivery_fee_always_charged"] is True
    assert data["online_payment_enabled"] is False
    assert data["whatsapp_mode"] == "LIVE_SUPPORT_ONLY"
    assert data["category_count"] == 2
    assert data["active_category_count"] == 1
    assert data["product_count"] == 3
    assert data["active_product_count"] == 2
    assert data["out_of_stock_product_count"] == 1
    assert data["low_stock_product_count"] == 1
    assert data["delivery_area_count"] == 2
    assert data["active_delivery_area_count"] == 1
    assert data["total_orders"] == 2
    assert data["active_orders"] == 1
    assert data["new_orders"] == 1
    assert data["delivered_orders"] == 1
    assert data["last_order_number"] == "#1002"
    assert data["last_audit_action"] == "MARKET_SETTINGS_UPDATED"
    assert data["last_backup_action"] == "BACKUP_EXPORTED"
    assert data["has_default_admin_username"] is True
    assert data["has_default_employee_username"] is True


def seed_status_data(db_session: Session, *, admin: User) -> None:
    settings = get_market_settings(db_session)
    settings.market_name = "Test Market"
    settings.minimum_order_amount = Decimal("250.00")
    settings.delivery_fee = Decimal("65.00")

    active_category = Category(name="Meyve", slug="meyve", is_active=True)
    inactive_category = Category(name="Temizlik", slug="temizlik", is_active=False)
    active_area = DeliveryArea(name="Merkez", slug="merkez", is_active=True)
    inactive_area = DeliveryArea(name="Uzak", slug="uzak", is_active=False)
    db_session.add_all(
        [active_category, inactive_category, active_area, inactive_area]
    )
    db_session.flush()

    db_session.add_all(
        [
            Product(
                category_id=active_category.id,
                name="Elma 1 kg",
                slug="elma-1-kg",
                price=Decimal("50.00"),
                stock_quantity=4,
                is_active=True,
            ),
            Product(
                category_id=active_category.id,
                name="Sut 1 L",
                slug="sut-1-l",
                price=Decimal("35.00"),
                stock_quantity=0,
                is_active=True,
            ),
            Product(
                category_id=inactive_category.id,
                name="Pasif Urun",
                slug="pasif-urun",
                price=Decimal("20.00"),
                stock_quantity=2,
                is_active=False,
            ),
        ]
    )
    db_session.add_all(
        [
            build_order(
                order_number="#1001",
                status="DELIVERED",
                delivery_area=active_area,
                created_at=datetime(2026, 9, 1, 10, 0, 0),
            ),
            build_order(
                order_number="#1002",
                status="NEW",
                delivery_area=active_area,
                created_at=datetime(2026, 9, 2, 11, 0, 0),
            ),
        ]
    )
    db_session.add_all(
        [
            AuditLog(
                actor_user_id=admin.id,
                actor_username_snapshot=admin.username,
                action="BACKUP_EXPORTED",
                target_type="backups",
                target_id=None,
                description="admin yedek indirdi.",
                created_at=datetime(2026, 9, 1, 12, 0, 0),
            ),
            AuditLog(
                actor_user_id=admin.id,
                actor_username_snapshot=admin.username,
                action="MARKET_SETTINGS_UPDATED",
                target_type="market_settings",
                target_id=1,
                description="admin market ayarlarini guncelledi.",
                created_at=datetime(2026, 9, 2, 12, 0, 0),
            ),
        ]
    )
    db_session.commit()


def build_order(
    *,
    order_number: str,
    status: str,
    delivery_area: DeliveryArea,
    created_at: datetime,
) -> Order:
    return Order(
        order_number=order_number,
        status=status,
        customer_first_name="Sait",
        customer_last_name="Musteri",
        phone="0532 111 22 33",
        delivery_area_id=delivery_area.id,
        delivery_area_name_snapshot=delivery_area.name,
        neighborhood="Merkez Mahallesi",
        street="Market Sokak",
        address_line="Market Sokak No 10",
        payment_method="CASH_ON_DELIVERY",
        unavailable_policy="CALL_CUSTOMER",
        subtotal=Decimal("100.00"),
        delivery_fee=Decimal("65.00"),
        grand_total=Decimal("165.00"),
        created_at=created_at,
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
