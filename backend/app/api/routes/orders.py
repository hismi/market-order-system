from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.order import Order
from app.schemas.order import OrderCreate, OrderCreateResponse, OrderTrackRead
from app.services.orders import (
    build_public_tracking_response,
    create_order,
    get_order_for_tracking,
)
from app.services.pricing import MinimumOrderError, PricingError

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("/track", response_model=OrderTrackRead)
def track_public_order(
    order_number: str = Query(min_length=3, max_length=32),
    phone: str = Query(min_length=10, max_length=32),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    order = get_order_for_tracking(
        db,
        order_number=order_number,
        phone=phone,
    )
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORDER_NOT_FOUND",
                "message": "Siparis bulunamadi.",
            },
        )
    return build_public_tracking_response(order)


@router.post("", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED)
def create_public_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
) -> Order:
    try:
        return create_order(db, payload)
    except MinimumOrderError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MINIMUM_ORDER_NOT_MET",
                "message": "Minimum siparis tutari saglanmadi.",
                "minimum_order_amount": f"{error.minimum:.2f}",
                "subtotal": f"{error.subtotal:.2f}",
                "remaining": f"{error.remaining:.2f}",
            },
        ) from error
    except PricingError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "ORDER_REJECTED",
                "message": str(error),
            },
        ) from error
