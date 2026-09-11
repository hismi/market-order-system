from app.core.config import Settings


DEVELOPMENT_JWT_SECRETS = {
    "change-this-development-secret",
    "test-secret",
}

DEVELOPMENT_PASSWORDS = {
    "Admin12345",
    "Employee12345",
}


def validate_runtime_settings(settings: Settings) -> None:
    if settings.app_env.lower() != "production":
        return

    errors: list[str] = []
    jwt_secret = (
        settings.jwt_secret.get_secret_value()
        if settings.jwt_secret is not None
        else ""
    )

    if len(jwt_secret) < 32:
        errors.append("JWT_SECRET en az 32 karakter olmalidir.")

    if is_placeholder_secret(jwt_secret):
        errors.append("JWT_SECRET production icin degistirilmelidir.")

    seed_passwords = [
        settings.seed_admin_password,
        settings.seed_employee_password,
    ]
    for seed_password in seed_passwords:
        if seed_password is None:
            continue
        if seed_password.get_secret_value() in DEVELOPMENT_PASSWORDS:
            errors.append("Varsayilan seed kullanici sifreleri production'da kullanilamaz.")
            break

    for origin in settings.cors_origin_list:
        if origin == "*":
            errors.append("Production CORS_ORIGINS '*' olamaz.")
        if origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1"):
            errors.append("Production CORS_ORIGINS localhost adresi icermemelidir.")

    if errors:
        raise RuntimeError(
            "Production guvenlik ayarlari eksik: " + " ".join(errors)
        )


def is_placeholder_secret(value: str) -> bool:
    normalized = value.strip().lower()
    return (
        normalized in DEVELOPMENT_JWT_SECRETS
        or "change-this" in normalized
        or "replace" in normalized
    )
