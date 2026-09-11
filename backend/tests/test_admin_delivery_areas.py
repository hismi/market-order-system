from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.audit_log import AuditLog
from app.models.delivery_area import DeliveryArea
from app.models.user import User
from app.services.users import create_user


def test_admin_can_create_delivery_area(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)

    response = client.post(
        "/api/admin/delivery-areas",
        headers=auth_headers(admin),
        json={
            "name": "Yeni Mahalle",
            "display_order": 50,
            "is_active": True,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Yeni Mahalle"
    assert data["slug"] == "yeni-mahalle"
    assert data["is_active"] is True
    assert db_session.query(AuditLog).count() == 1


def test_admin_can_deactivate_delivery_area_and_hide_it_from_public_checkout(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)
    active_area = DeliveryArea(name="Merkez", slug="merkez", is_active=True)
    passive_area = DeliveryArea(name="Eski Bolge", slug="eski-bolge", is_active=True)
    db_session.add_all([active_area, passive_area])
    db_session.commit()

    response = client.patch(
        f"/api/admin/delivery-areas/{passive_area.id}",
        headers=auth_headers(admin),
        json={
            "name": "Eski Bolge",
            "slug": "eski-bolge",
            "display_order": 20,
            "is_active": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    public_response = client.get("/api/delivery-areas")
    assert public_response.status_code == 200
    assert [area["slug"] for area in public_response.json()] == ["merkez"]


def test_employee_cannot_manage_delivery_areas(
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
        "/api/admin/delivery-areas",
        headers=auth_headers(employee),
    )

    assert response.status_code == 403


def test_admin_delivery_area_rejects_duplicate_slug(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)
    db_session.add(DeliveryArea(name="Merkez", slug="merkez", is_active=True))
    db_session.commit()

    response = client.post(
        "/api/admin/delivery-areas",
        headers=auth_headers(admin),
        json={
            "name": "Baska Merkez",
            "slug": "merkez",
            "display_order": 30,
            "is_active": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == (
        "Bu teslimat bolgesi slug degeri zaten kullaniliyor."
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
