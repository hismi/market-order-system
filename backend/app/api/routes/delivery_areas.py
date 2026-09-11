from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.delivery_area import DeliveryArea
from app.schemas.delivery_area import DeliveryAreaRead
from app.services.delivery_areas import list_active_delivery_areas

router = APIRouter(prefix="/api/delivery-areas", tags=["delivery-areas"])


@router.get("", response_model=list[DeliveryAreaRead])
def read_delivery_areas(db: Session = Depends(get_db)) -> list[DeliveryArea]:
    return list_active_delivery_areas(db)
