from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.database.session import get_db
from app.models.delivery_area import DeliveryArea
from app.models.user import User
from app.schemas.delivery_area import AdminDeliveryAreaRead, DeliveryAreaWrite
from app.services.delivery_areas import (
    create_delivery_area,
    list_admin_delivery_areas,
    update_delivery_area,
)

router = APIRouter(prefix="/api/admin/delivery-areas", tags=["admin-delivery-areas"])


@router.get("", response_model=list[AdminDeliveryAreaRead])
def read_admin_delivery_areas(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> list[DeliveryArea]:
    _ = current_user
    return list_admin_delivery_areas(db)


@router.post(
    "",
    response_model=AdminDeliveryAreaRead,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_delivery_area(
    payload: DeliveryAreaWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> DeliveryArea:
    try:
        return create_delivery_area(db, payload=payload, actor=current_user)
    except ValueError as error:
        raise bad_request(error) from error


@router.patch("/{delivery_area_id}", response_model=AdminDeliveryAreaRead)
def update_admin_delivery_area(
    delivery_area_id: int,
    payload: DeliveryAreaWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> DeliveryArea:
    try:
        return update_delivery_area(
            db,
            delivery_area_id=delivery_area_id,
            payload=payload,
            actor=current_user,
        )
    except ValueError as error:
        raise bad_request(error) from error


def bad_request(error: ValueError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": "ADMIN_DELIVERY_AREA_REJECTED",
            "message": str(error),
        },
    )
