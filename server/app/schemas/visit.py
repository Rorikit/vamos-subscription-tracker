from datetime import date, datetime
from decimal import Decimal

from app.schemas.common import ApiModel, MembershipTypeSnapshot, ParticipantSnapshot, TeacherSnapshot


class VisitRead(ApiModel):
    id: int
    participant_id: int
    membership_id: int
    teacher_id: int
    visit_date: date
    lesson_price: Decimal | None = None
    teacher_lesson_rate: Decimal | None = None
    teacher_earning: Decimal | None = None
    school_earning: Decimal | None = None
    is_cancelled: bool
    participant: ParticipantSnapshot | None = None
    teacher: TeacherSnapshot | None = None
    membership_type: MembershipTypeSnapshot | None = None
    created_at: datetime
    updated_at: datetime
