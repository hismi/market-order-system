from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.delivery_area import DeliveryArea
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.services.market_settings import get_market_acceptance_status, get_market_settings

ACTIVE_ORDER_STATUSES = {"NEW", "PREPARING", "ON_THE_WAY"}
BACKUP_AUDIT_ACTIONS = {"BACKUP_EXPORTED", "BACKUP_RESTORED"}


def build_admin_system_status(
    db: Session,
    *,
    settings: Settings,
) -> dict[str, object]:
    market_settings = get_market_settings(db)
    market_acceptance = get_market_acceptance_status(
        market_settings,
        app_settings=settings,
    )
    last_order = get_last_order(db)
    last_audit_log = get_last_audit_log(db)
    last_backup_log = get_last_backup_log(db)

    return {
        "checked_at": datetime.now(timezone.utc),
        "api_status": "OK",
        "app_env": settings.app_env,
        "market_name": market_settings.market_name,
        "market_is_open": market_settings.is_open,
        "market_accepting_orders": market_acceptance.accepting_orders,
        "market_closed_reason": market_acceptance.closed_reason,
        "market_timezone": market_acceptance.timezone,
        "minimum_order_amount": market_settings.minimum_order_amount,
        "delivery_fee": market_settings.delivery_fee,
        "delivery_fee_always_charged": True,
        "online_payment_enabled": False,
        "whatsapp_mode": "LIVE_SUPPORT_ONLY",
        "category_count": count_rows(db, Category),
        "active_category_count": count_rows(db, Category, Category.is_active.is_(True)),
        "product_count": count_rows(db, Product),
        "active_product_count": count_rows(db, Product, Product.is_active.is_(True)),
        "out_of_stock_product_count": count_rows(
            db,
            Product,
            Product.is_active.is_(True),
            Product.stock_quantity <= 0,
        ),
        "low_stock_product_count": count_rows(
            db,
            Product,
            Product.is_active.is_(True),
            Product.stock_quantity > 0,
            Product.stock_quantity <= 5,
        ),
        "delivery_area_count": count_rows(db, DeliveryArea),
        "active_delivery_area_count": count_rows(
            db,
            DeliveryArea,
            DeliveryArea.is_active.is_(True),
        ),
        "total_orders": count_rows(db, Order),
        "active_orders": count_rows(db, Order, Order.status.in_(ACTIVE_ORDER_STATUSES)),
        "new_orders": count_rows(db, Order, Order.status == "NEW"),
        "preparing_orders": count_rows(db, Order, Order.status == "PREPARING"),
        "on_the_way_orders": count_rows(db, Order, Order.status == "ON_THE_WAY"),
        "delivered_orders": count_rows(db, Order, Order.status == "DELIVERED"),
        "cancelled_orders": count_rows(db, Order, Order.status == "CANCELLED"),
        "last_order_number": last_order.order_number if last_order else None,
        "last_order_at": last_order.created_at if last_order else None,
        "last_audit_action": last_audit_log.action if last_audit_log else None,
        "last_audit_at": last_audit_log.created_at if last_audit_log else None,
        "last_backup_action": last_backup_log.action if last_backup_log else None,
        "last_backup_at": last_backup_log.created_at if last_backup_log else None,
        "has_default_admin_username": user_exists(db, username="admin", role="ADMIN"),
        "has_default_employee_username": user_exists(
            db,
            username="employee",
            role="EMPLOYEE",
        ),
    }


def count_rows(db: Session, model: type, *conditions) -> int:
    query = select(func.count()).select_from(model)
    for condition in conditions:
        query = query.where(condition)
    return int(db.scalar(query) or 0)


def get_last_order(db: Session) -> Order | None:
    return db.scalar(
        select(Order).order_by(Order.created_at.desc(), Order.id.desc()).limit(1)
    )


def get_last_audit_log(db: Session) -> AuditLog | None:
    return db.scalar(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(1)
    )


def get_last_backup_log(db: Session) -> AuditLog | None:
    return db.scalar(
        select(AuditLog)
        .where(AuditLog.action.in_(BACKUP_AUDIT_ACTIONS))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(1)
    )


def user_exists(db: Session, *, username: str, role: str) -> bool:
    return (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.username == username, User.role == role)
        )
        or 0
    ) > 0
