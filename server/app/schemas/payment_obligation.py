from datetime import date
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.schemas.common import ApiModel


class PaymentObligationRead(ApiModel):
    id: int
    name: str
    planned_amount: Decimal
    actual_amount: Decimal | None
    display_amount: Decimal
    due_date: date
    reminder_day: int
    paid: bool
    paid_at: date | None = None
    paid_by_user_id: int | None = None
    paid_by_name: str | None = None
    status: str
    is_variable: bool
    comment: str | None = None


class PaymentObligationPay(BaseModel):
    actual_amount: Decimal | None = None

    @field_validator("actual_amount")
    @classmethod
    def validate_actual_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value <= 0:
            raise ValueError("actual_amount must be greater than 0")
        return value


class PaymentObligationSummary(ApiModel):
    year: int
    month: int
    total_count: int
    unpaid_count: int
    due_today_count: int
    overdue_count: int
    paid_count: int
    items: list[PaymentObligationRead]
