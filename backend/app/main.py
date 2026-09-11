from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import models
from app.api.routes import (
    admin_audit_logs,
    admin_backups,
    admin_catalog,
    admin_delivery_areas,
    admin_orders,
    admin_reports,
    admin_system_status,
    admin_users,
    auth,
    catalog,
    delivery_areas,
    employee_orders,
    health,
    market_settings,
    orders,
)
from app.core.config import get_settings
from app.core.runtime_security import validate_runtime_settings
from app.database.base import Base
from app.database.migrations import ensure_sqlite_dev_schema
from app.database.session import SessionLocal, engine
from app.services.catalog import seed_catalog_if_empty
from app.services.delivery_areas import seed_delivery_areas_if_empty
from app.services.market_settings import get_market_settings
from app.services.users import seed_users_if_configured


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = models
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_dev_schema(engine)
    with SessionLocal() as db:
        get_market_settings(db)
        seed_delivery_areas_if_empty(db)
        seed_catalog_if_empty(db)
        seed_users_if_configured(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    validate_runtime_settings(settings)
    upload_path = Path(settings.upload_directory)
    upload_path.mkdir(parents=True, exist_ok=True)

    api = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    if settings.cors_origin_list:
        api.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    api.mount("/uploads", StaticFiles(directory=upload_path), name="uploads")

    api.include_router(health.router)
    api.include_router(auth.router)
    api.include_router(market_settings.router)
    api.include_router(catalog.router)
    api.include_router(delivery_areas.router)
    api.include_router(orders.router)
    api.include_router(employee_orders.router)
    api.include_router(admin_catalog.router)
    api.include_router(admin_delivery_areas.router)
    api.include_router(admin_orders.router)
    api.include_router(admin_reports.router)
    api.include_router(admin_system_status.router)
    api.include_router(admin_audit_logs.router)
    api.include_router(admin_backups.router)
    api.include_router(admin_users.router)
    return api


app = create_app()
