from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.database.session import get_db
from app.models.user import User
from app.schemas.admin_report import OrderReportRead
from app.services.reports import build_order_report

router = APIRouter(prefix="/api/admin/reports", tags=["admin-reports"])


AdminUser = Depends(require_roles("ADMIN"))


@router.get("/orders", response_model=OrderReportRead)
def read_order_report(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = AdminUser,
) -> dict[str, object]:
    _ = current_user
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "REPORT_RANGE_REJECTED",
                "message": "Baslangic tarihi bitis tarihinden sonra olamaz.",
            },
        )
    return build_order_report(db, start_date=start_date, end_date=end_date)
