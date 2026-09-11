from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Market Order System API"
    app_env: str = "development"
    app_timezone: str = "Europe/Istanbul"
    database_url: str = "sqlite:///./market_order_system.sqlite3"
    cors_origins: str = (
        "http://127.0.0.1:5500,http://localhost:5500,"
        "http://127.0.0.1:5501,http://localhost:5501,"
        "http://127.0.0.1:5502,http://localhost:5502"
    )
    jwt_secret: SecretStr | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    seed_admin_username: str | None = None
    seed_admin_password: SecretStr | None = None
    seed_employee_username: str | None = None
    seed_employee_password: SecretStr | None = None
    upload_directory: str = "uploads"
    max_product_image_bytes: int = 2 * 1024 * 1024
    max_backup_upload_bytes: int = 50 * 1024 * 1024
    login_rate_limit_max_attempts: int = Field(default=5, ge=1, le=50)
    login_rate_limit_window_seconds: int = Field(default=600, ge=60, le=86400)
    login_rate_limit_lockout_seconds: int = Field(default=900, ge=60, le=86400)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    def get_jwt_secret(self) -> str:
        if self.jwt_secret is None:
            raise RuntimeError("JWT_SECRET .env dosyasinda tanimli olmalidir.")
        return self.jwt_secret.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()
