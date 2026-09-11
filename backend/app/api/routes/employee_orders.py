from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.database.session import get_db
from app.models.order import Order
from app.models.user import User
from app.schemas.order import EmployeeOrderRead, RejectOrderRequest
from app.services.orders import change_order_status, list_orders
from app.services.pricing import PricingError

router = APIRouter(prefix="/api/employee/orders", tags=["employee-orders"])


EmployeeUser = Depends(require_roles("EMPLOYEE", "ADMIN"))


@router.get("", response_model=list[EmployeeOrderRead])
def read_employee_orders(
    order_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = EmployeeUser,
) -> list[Order]:
    _ = current_user
    try:
        return list_orders(db, status=order_status)
    except PricingError as error:
        raise bad_request(error) from error


@router.post("/{order_id}/approve", response_model=EmployeeOrderRead)
def approve_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = EmployeeUser,
) -> Order:
    return transition_order(db, order_id, "PREPARING", current_user)


@router.post("/{order_id}/reject", response_model=EmployeeOrderRead)
def reject_order(
    order_id: int,
    payload: RejectOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = EmployeeUser,
) -> Order:
    try:
        return change_order_status(
            db,
            order_id=order_id,
            next_status="CANCELLED",
            actor=current_user,
            cancellation_reason=payload.reason,
        )
    except PricingError as error:
        raise bad_request(error) from error


@router.post("/{order_id}/on-the-way", response_model=EmployeeOrderRead)
def mark_order_on_the_way(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = EmployeeUser,
) -> Order:
    return transition_order(db, order_id, "ON_THE_WAY", current_user)


@router.post("/{order_id}/delivered", response_model=EmployeeOrderRead)
def mark_order_delivered(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = EmployeeUser,
) -> Order:
    return transition_order(db, order_id, "DELIVERED", current_user)


def transition_order(
    db: Session,
    order_id: int,
    next_status: str,
    current_user: User,
) -> Order:
    try:
        return change_order_status(
            db,
            order_id=order_id,
            next_status=next_status,
            actor=current_user,
        )
    except PricingError as error:
        raise bad_request(error) from error


def bad_request(error: PricingError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": "ORDER_OPERATION_REJECTED",
            "message": str(error),
        },
    )
