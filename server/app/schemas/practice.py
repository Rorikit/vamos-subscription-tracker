from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.models.practice import PracticeRentalStatus
from app.schemas.common import ApiModel


class PracticeTariffBase(BaseModel):
    name: str
    price: Decimal
    is_active: bool = True
    sort_order: int = 100

    @field_validator("price")
    @classmethod
    def validate_price(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("price must be positive")
        return value


class PracticeTariffCreate(PracticeTariffBase):
    pass


class PracticeTariffUpdate(BaseModel):
    name: str | None = None
    price: Decimal | None = None
    is_active: bool | None = None
    sort_order: int | None = None

    @field_validator("price")
    @classmethod
    def validate_price(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value <= 0:
            raise ValueError("price must be positive")
        return value


class PracticeTariffRead(PracticeTariffBase, ApiModel):
    id: int
    created_at: datetime
    updated_at: datetime


class PracticeRentalCreate(BaseModel):
    registered_teacher_id: int | None = None
    customer_name: str
    tariff_id: int
    practiced_at: datetime
    comment: str | None = None


class PracticeRentalRead(ApiModel):
    id: int
    registered_teacher_id: int | None
    customer_name: str
    tariff_id: int | None
    tariff_name_snapshot: str
    amount: Decimal
    practiced_at: datetime
    status: PracticeRentalStatus
    comment: str | None
    created_by_user_id: int
    created_by_name: str | None = None
    cancelled_at: datetime | None
    cancelled_by_user_id: int | None
    created_at: datetime
    updated_at: datetime


class PracticeRentalSummary(ApiModel):
    income_total: Decimal
    rentals_count: int
    average_check: Decimal
