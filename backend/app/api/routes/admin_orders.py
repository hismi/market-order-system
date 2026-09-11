from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.database.session import get_db
from app.models.order import Order
from app.models.user import User
from app.schemas.order import AdminOrderSummary, EmployeeOrderRead
from app.services.orders import get_order_summary, list_orders
from app.services.pricing import PricingError

router = APIRouter(prefix="/api/admin/orders", tags=["admin-orders"])


AdminUser = Depends(require_roles("ADMIN"))


@router.get("/summary", response_model=AdminOrderSummary)
def read_admin_order_summary(
    db: Session = Depends(get_db),
    current_user: User = AdminUser,
) -> dict[str, object]:
    _ = current_user
    return get_order_summary(db)


@router.get("", response_model=list[EmployeeOrderRead])
def read_admin_orders(
    order_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = AdminUser,
) -> list[Order]:
    _ = current_user
    try:
        return list_orders(db, status=order_status, limit=limit)
    except PricingError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "ORDER_OPERATION_REJECTED",
                "message": str(error),
            },
        ) from error
