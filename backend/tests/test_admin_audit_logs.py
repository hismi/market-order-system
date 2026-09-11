from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.audit import write_audit_log
from app.services.users import create_user


def test_admin_audit_logs_require_admin_role(
    client: TestClient,
    db_session: Session,
) -> None:
    response_without_auth = client.get("/api/admin/audit-logs")
    assert response_without_auth.status_code == 401

    employee = create_user(
        db_session,
        username="employee",
        password="Employee12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )

    response_with_employee = client.get(
        "/api/admin/audit-logs",
        headers=auth_headers(employee),
    )
    assert response_with_employee.status_code == 403


def test_admin_can_list_audit_logs_newest_first(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session)
    write_audit_log(
        db_session,
        actor=admin,
        action="PRODUCT_CREATED",
        target_type="products",
        target_id=1,
        description="admin urun olusturdu: Elma",
    )
    write_audit_log(
        db_session,
        actor=admin,
        action="ORDER_STATUS_CHANGED",
        target_type="orders",
        target_id=2,
        description="admin siparis #1001 durumunu NEW -> PREPARING olarak degistirdi.",
    )
    db_session.commit()
    first_log = db_session.query(AuditLog).filter_by(action="PRODUCT_CREATED").one()
    second_log = (
        db_session.query(AuditLog)
        .filter_by(action="ORDER_STATUS_CHANGED")
        .one()
    )
    first_log.created_at = datetime(2026, 9, 1, 10, 0, 0)
    second_log.created_at = datetime(2026, 9, 2, 10, 0, 0)
    db_session.commit()

    response = client.get(
        "/api/admin/audit-logs",
        headers=auth_headers(admin),
        params={"limit": 1},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["action"] == "ORDER_STATUS_CHANGED"
    assert data[0]["actor_username_snapshot"] == "admin"


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
