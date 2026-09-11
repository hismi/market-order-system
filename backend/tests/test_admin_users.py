from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.users import create_user


def test_admin_users_require_admin_role(
    client: TestClient,
    db_session: Session,
) -> None:
    response_without_auth = client.get("/api/admin/users")
    assert response_without_auth.status_code == 401

    employee = create_user(
        db_session,
        username="employee",
        password="Employee12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )

    response_with_employee = client.get(
        "/api/admin/users",
        headers=auth_headers(employee),
    )
    assert response_with_employee.status_code == 403


def test_admin_can_create_employee_and_list_users(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)

    create_response = client.post(
        "/api/admin/users",
        headers=auth_headers(admin),
        json={
            "username": "Kasiyer",
            "full_name": "Kasiyer Bir",
            "role": "EMPLOYEE",
            "password": "Employee12345",
            "is_active": True,
        },
    )

    assert create_response.status_code == 201
    created_user = create_response.json()
    assert created_user["username"] == "kasiyer"
    assert created_user["role"] == "EMPLOYEE"
    assert created_user["is_active"] is True

    list_response = client.get(
        "/api/admin/users",
        headers=auth_headers(admin),
    )
    assert list_response.status_code == 200
    assert {item["username"] for item in list_response.json()} == {"admin", "kasiyer"}
    assert db_session.query(AuditLog).count() == 1


def test_admin_user_create_rejects_duplicate_username(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)
    create_user(
        db_session,
        username="kasiyer",
        password="Employee12345",
        full_name="Kasiyer Bir",
        role="EMPLOYEE",
    )

    response = client.post(
        "/api/admin/users",
        headers=auth_headers(admin),
        json={
            "username": "kasiyer",
            "full_name": "Kasiyer Iki",
            "role": "EMPLOYEE",
            "password": "Employee12345",
            "is_active": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Bu kullanici adi zaten kullaniliyor."


def test_admin_can_deactivate_employee_and_block_login(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)
    employee = create_user(
        db_session,
        username="employee",
        password="Employee12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )

    update_response = client.patch(
        f"/api/admin/users/{employee.id}",
        headers=auth_headers(admin),
        json={
            "is_active": False,
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["is_active"] is False

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "employee",
            "password": "Employee12345",
        },
    )
    assert login_response.status_code == 401


def test_admin_can_reset_employee_password(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)
    employee = create_user(
        db_session,
        username="employee",
        password="OldPass12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )

    update_response = client.patch(
        f"/api/admin/users/{employee.id}",
        headers=auth_headers(admin),
        json={
            "password": "NewPass12345",
        },
    )

    assert update_response.status_code == 200
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "employee",
            "password": "NewPass12345",
        },
    )
    assert login_response.status_code == 200


def test_admin_cannot_deactivate_or_demote_self(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)

    deactivate_response = client.patch(
        f"/api/admin/users/{admin.id}",
        headers=auth_headers(admin),
        json={
            "is_active": False,
        },
    )
    assert deactivate_response.status_code == 400
    assert deactivate_response.json()["detail"]["message"] == (
        "Kendi hesabinizi pasife alamazsiniz."
    )

    demote_response = client.patch(
        f"/api/admin/users/{admin.id}",
        headers=auth_headers(admin),
        json={
            "role": "EMPLOYEE",
        },
    )
    assert demote_response.status_code == 400
    assert demote_response.json()["detail"]["message"] == (
        "Kendi admin yetkinizi kaldiramazsiniz."
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
