from datetime import date, datetime
from decimal import Decimal

from app.models.membership_finance import FinancialDirection, FinancialEntryType
from app.schemas.common import ApiModel


class MembershipRevisionRead(ApiModel):
    id: int
    membership_id: int
    revision_number: int
    membership_type_id: int
    price: Decimal
    lesson_count: int
    lesson_price: Decimal
    teacher_lesson_rate: Decimal
    effective_from: date
    effective_to: date | None
    change_reason: str | None
    created_by_operator_id: int | None
    created_at: datetime


class MembershipChangeRead(ApiModel):
    id: int
    participant_id: int
    old_membership_id: int
    new_membership_id: int
    effective_at: date
    transfer_mode: str
    transferred_lessons: int
    transferred_value: Decimal
    reason: str
    created_by_operator_id: int | None
    created_at: datetime


class FinancialEntryRead(ApiModel):
    id: int
    participant_id: int | None
    membership_id: int | None
    membership_revision_id: int | None
    visit_id: int | None
    entry_type: FinancialEntryType
    direction: FinancialDirection
    amount: Decimal
    effective_date: date
    source_type: str
    source_id: int
    reverses_entry_id: int | None
    description: str | None
    created_at: datetime
