import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.audit_log import AuditLog
from app.services.login_rate_limiter import login_rate_limiter
from app.services.users import create_user


@pytest.fixture(autouse=True)
def clear_login_rate_limiter():
    login_rate_limiter.clear()
    yield
    login_rate_limiter.clear()


def test_login_returns_token_and_me_returns_current_user(
    client: TestClient,
    db_session: Session,
) -> None:
    create_user(
        db_session,
        username="employee",
        password="Employee12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "employee",
            "password": "Employee12345",
        },
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    assert token

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["username"] == "employee"
    assert me_response.json()["role"] == "EMPLOYEE"


def test_login_rejects_wrong_password(
    client: TestClient,
    db_session: Session,
) -> None:
    create_user(
        db_session,
        username="employee",
        password="Employee12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )

    response = client.post(
        "/api/auth/login",
        json={
            "username": "employee",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401


def test_login_rate_limit_blocks_repeated_failed_attempts(
    client: TestClient,
    db_session: Session,
) -> None:
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        jwt_secret="test-secret-for-rate-limit-tests",
        login_rate_limit_max_attempts=2,
        login_rate_limit_window_seconds=60,
        login_rate_limit_lockout_seconds=120,
    )
    create_user(
        db_session,
        username="employee-rate-limit",
        password="Employee12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )

    for _ in range(2):
        response = client.post(
            "/api/auth/login",
            json={
                "username": "employee-rate-limit",
                "password": "wrong-password",
            },
        )
        assert response.status_code == 401

    blocked_response = client.post(
        "/api/auth/login",
        json={
            "username": "employee-rate-limit",
            "password": "Employee12345",
        },
    )

    assert blocked_response.status_code == 429
    assert blocked_response.json()["detail"]["code"] == "LOGIN_RATE_LIMITED"
    assert int(blocked_response.headers["Retry-After"]) > 0


def test_successful_login_clears_failed_login_counter(
    client: TestClient,
    db_session: Session,
) -> None:
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        jwt_secret="test-secret-for-rate-limit-tests",
        login_rate_limit_max_attempts=2,
        login_rate_limit_window_seconds=60,
        login_rate_limit_lockout_seconds=120,
    )
    create_user(
        db_session,
        username="employee-reset",
        password="Employee12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )

    failed_response = client.post(
        "/api/auth/login",
        json={
            "username": "employee-reset",
            "password": "wrong-password",
        },
    )
    assert failed_response.status_code == 401

    successful_response = client.post(
        "/api/auth/login",
        json={
            "username": "employee-reset",
            "password": "Employee12345",
        },
    )
    assert successful_response.status_code == 200

    next_failed_response = client.post(
        "/api/auth/login",
        json={
            "username": "employee-reset",
            "password": "wrong-password",
        },
    )
    assert next_failed_response.status_code == 401


def test_authenticated_user_can_change_own_password(
    client: TestClient,
    db_session: Session,
) -> None:
    create_user(
        db_session,
        username="employee-password",
        password="Employee12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )
    token = login_and_get_token(client, "employee-password", "Employee12345")

    response = client.patch(
        "/api/auth/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "Employee12345",
            "new_password": "Employee54321",
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Sifre guncellendi."
    assert (
        db_session.query(AuditLog)
        .filter_by(action="PASSWORD_CHANGED", target_type="users")
        .count()
        == 1
    )

    old_login_response = client.post(
        "/api/auth/login",
        json={
            "username": "employee-password",
            "password": "Employee12345",
        },
    )
    new_login_response = client.post(
        "/api/auth/login",
        json={
            "username": "employee-password",
            "password": "Employee54321",
        },
    )

    assert old_login_response.status_code == 401
    assert new_login_response.status_code == 200


def test_password_change_rejects_wrong_current_password(
    client: TestClient,
    db_session: Session,
) -> None:
    create_user(
        db_session,
        username="employee-wrong-current",
        password="Employee12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )
    token = login_and_get_token(client, "employee-wrong-current", "Employee12345")

    response = client.patch(
        "/api/auth/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "Wrong12345",
            "new_password": "Employee54321",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "PASSWORD_CHANGE_REJECTED"


def test_password_change_rejects_same_password(
    client: TestClient,
    db_session: Session,
) -> None:
    create_user(
        db_session,
        username="employee-same-password",
        password="Employee12345",
        full_name="Market Calisani",
        role="EMPLOYEE",
    )
    token = login_and_get_token(client, "employee-same-password", "Employee12345")

    response = client.patch(
        "/api/auth/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "Employee12345",
            "new_password": "Employee12345",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "PASSWORD_CHANGE_REJECTED"


def login_and_get_token(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])
