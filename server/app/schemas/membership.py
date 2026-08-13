from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.membership import MembershipStatus
from app.schemas.common import ApiModel, MembershipTypeSnapshot, ParticipantSnapshot


class MembershipCreate(BaseModel):
    participant_id: int
    membership_type_id: int
    teacher_lesson_rate: Decimal = Field(ge=0)


class MembershipUpdate(BaseModel):
    total_lessons: int | None = Field(default=None, gt=0)
    remaining_lessons: int | None = Field(default=None, ge=0)
    price: Decimal | None = Field(default=None, ge=0)
    teacher_lesson_rate: Decimal | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None


class MembershipRead(ApiModel):
    id: int
    participant_id: int
    membership_type_id: int
    total_lessons: int
    remaining_lessons: int
    price: Decimal
    teacher_lesson_rate: Decimal
    start_date: date
    end_date: date
    status: MembershipStatus
    is_currently_active: bool
    paid_amount: Decimal
    participant: ParticipantSnapshot | None = None
    membership_type: MembershipTypeSnapshot | None = None
    created_at: datetime
    updated_at: datetime
