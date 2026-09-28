from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, model_validator

from app.schemas.common import ApiModel


class MembershipTypeBase(BaseModel):
    name: str
    lesson_count: int
    price: Decimal
    cash_price: Decimal | None = None
    card_price: Decimal | None = None
    validity_days: int
    description: str | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def validate_payment_prices(self):
        cash = self.cash_price if self.cash_price is not None else self.price
        card = self.card_price if self.card_price is not None else self.price
        if cash <= 0 or card <= 0:
            raise ValueError("Цены должны быть больше нуля")
        if card < cash:
            raise ValueError("Цена картой не может быть ниже цены наличными")
        self.cash_price = cash
        self.card_price = card
        self.price = cash
        return self


class MembershipTypeCreate(MembershipTypeBase):
    pass


class MembershipTypeUpdate(BaseModel):
    name: str | None = None
    lesson_count: int | None = None
    price: Decimal | None = None
    cash_price: Decimal | None = None
    card_price: Decimal | None = None
    validity_days: int | None = None
    description: str | None = None
    is_active: bool | None = None


class MembershipTypeRead(MembershipTypeBase, ApiModel):
    id: int
    created_at: datetime
    updated_at: datetime
