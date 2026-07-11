from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.membership import MembershipStatus
from app.schemas.common import ApiModel, MembershipTypeSnapshot, ParticipantSnapshot


class MembershipCreate(BaseModel):
    participant_id: int
    membership_type_id: int


class MembershipRead(ApiModel):
    id: int
    participant_id: int
    membership_type_id: int
    total_lessons: int
    remaining_lessons: int
    price: Decimal
    start_date: date
    end_date: date
    status: MembershipStatus
    is_currently_active: bool
    paid_amount: Decimal
    participant: ParticipantSnapshot | None = None
    membership_type: MembershipTypeSnapshot | None = None
    created_at: datetime
    updated_at: datetime
