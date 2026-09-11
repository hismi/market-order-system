import pytest

from app.core.config import Settings
from app.core.runtime_security import validate_runtime_settings


def test_development_settings_skip_production_security_gate() -> None:
    settings = Settings(
        app_env="development",
        jwt_secret="change-this-development-secret",
        seed_admin_password="Admin12345",
        cors_origins="http://127.0.0.1:5500",
    )

    validate_runtime_settings(settings)


def test_production_settings_reject_dev_defaults() -> None:
    settings = Settings(
        app_env="production",
        jwt_secret="change-this-development-secret",
        seed_admin_password="Admin12345",
        seed_employee_password="Employee12345",
        cors_origins="http://127.0.0.1:5500",
    )

    with pytest.raises(RuntimeError) as error:
        validate_runtime_settings(settings)

    message = str(error.value)
    assert "JWT_SECRET" in message
    assert "Varsayilan seed kullanici sifreleri" in message
    assert "localhost" in message


def test_production_settings_accept_safe_values() -> None:
    settings = Settings(
        app_env="production",
        jwt_secret="z6EmAhJ2oUfz7VXLjZEcqRNFEk8vvruNVJ7Wd1s5Wf8",
        seed_admin_username=None,
        seed_admin_password=None,
        seed_employee_username=None,
        seed_employee_password=None,
        cors_origins="https://market.example.com",
    )

    validate_runtime_settings(settings)
