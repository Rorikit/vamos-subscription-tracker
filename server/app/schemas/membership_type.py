from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import ApiModel


class MembershipTypeBase(BaseModel):
    name: str
    lesson_count: int
    price: Decimal
    validity_days: int
    description: str | None = None
    is_active: bool = True


class MembershipTypeCreate(MembershipTypeBase):
    pass


class MembershipTypeUpdate(BaseModel):
    name: str | None = None
    lesson_count: int | None = None
    price: Decimal | None = None
    validity_days: int | None = None
    description: str | None = None
    is_active: bool | None = None


class MembershipTypeRead(MembershipTypeBase, ApiModel):
    id: int
    created_at: datetime
    updated_at: datetime

