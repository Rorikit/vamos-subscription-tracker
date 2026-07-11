from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import ApiModel, ParticipantSnapshot


class PaymentCreate(BaseModel):
    participant_id: int
    membership_id: int
    amount: Decimal
    payment_date: date | None = None
    payment_method: str = "cash"
    comment: str | None = None


class PaymentRead(ApiModel):
    id: int
    participant_id: int
    membership_id: int
    amount: Decimal
    payment_date: date
    payment_method: str
    comment: str | None = None
    is_cancelled: bool
    participant: ParticipantSnapshot | None = None
    created_at: datetime
    updated_at: datetime

