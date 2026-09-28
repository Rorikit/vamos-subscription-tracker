from datetime import date
from decimal import Decimal

from app.schemas.common import ApiModel


class NotificationItem(ApiModel):
    type: str
    count: int
    severity: str
    action: str
    amount: Decimal | None = None
    upcoming_count: int = 0
    due_today_count: int = 0
    overdue_count: int = 0
    nearest_due_date: date | None = None


class NotificationSummary(ApiModel):
    items: list[NotificationItem]
