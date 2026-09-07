from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Operator
from app.schemas.notification import NotificationSummary
from app.services.auth import get_current_operator
from app.services.notifications import get_notification_summary

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/summary", response_model=NotificationSummary)
def summary(
    db: Session = Depends(get_db),
    operator: Operator = Depends(get_current_operator),
):
    return get_notification_summary(db, operator)
