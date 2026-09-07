from decimal import Decimal

from app.schemas.common import ApiModel


class NotificationItem(ApiModel):
    type: str
    count: int
    severity: str
    action: str
    amount: Decimal | None = None


class NotificationSummary(ApiModel):
    items: list[NotificationItem]
