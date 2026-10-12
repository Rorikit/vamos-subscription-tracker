from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.common import ApiModel

class WaterReceiptCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2, allow_inf_nan=False)
    received_on: date
    payment_method: Literal["cash", "card"]
    comment: str | None = Field(default=None, max_length=2000)
    request_id: UUID

class WaterReceiptRead(ApiModel):
    id: int
    amount: Decimal
    received_on: date
    payment_method: Literal["cash", "card"]
    status: Literal["active", "cancelled"]
    comment: str | None
    created_by_user_id: int
    created_by_name: str | None
    cancelled_at: datetime | None
    created_at: datetime

class WaterSummary(ApiModel):
    income_total: Decimal
    receipts_count: int
