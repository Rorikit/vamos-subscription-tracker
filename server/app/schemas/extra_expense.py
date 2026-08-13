from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.models.extra_expense import ExtraExpenseStatus
from app.schemas.common import ApiModel

MAX_EXTRA_EXPENSE_AMOUNT = Decimal("10000000")


class ExtraExpenseBase(BaseModel):
    title: str
    amount: Decimal
    expense_date: date
    comment: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("title is required")
        return title

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("amount must be positive")
        if value > MAX_EXTRA_EXPENSE_AMOUNT:
            raise ValueError("amount is too large")
        return value


class ExtraExpenseCreate(ExtraExpenseBase):
    pass


class ExtraExpenseUpdate(BaseModel):
    title: str | None = None
    amount: Decimal | None = None
    expense_date: date | None = None
    comment: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        title = value.strip()
        if not title:
            raise ValueError("title is required")
        return title

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("amount must be positive")
        if value > MAX_EXTRA_EXPENSE_AMOUNT:
            raise ValueError("amount is too large")
        return value


class ExtraExpenseRead(ApiModel):
    id: int
    title: str
    amount: Decimal
    expense_date: date
    comment: str | None
    status: ExtraExpenseStatus
    created_by_user_id: int
    created_by_name: str | None = None
    cancelled_at: datetime | None
    cancelled_by_user_id: int | None
    created_at: datetime
    updated_at: datetime


class ExtraExpenseSummary(ApiModel):
    expenses_total: Decimal
    expenses_count: int
    average_expense: Decimal
