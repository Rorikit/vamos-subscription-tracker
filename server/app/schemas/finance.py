from datetime import date
from decimal import Decimal

from app.schemas.common import ApiModel
from app.schemas.membership import MembershipRead
from app.schemas.payment import PaymentRead
from app.schemas.visit import VisitRead


class TeacherEarningVisit(ApiModel):
    visit_id: int
    visit_date: date
    participant_id: int
    participant_name: str
    membership_id: int
    membership_name: str
    lesson_price: Decimal
    teacher_lesson_rate: Decimal
    teacher_earning: Decimal
    school_earning: Decimal
    is_cancelled: bool


class TeacherEarning(ApiModel):
    teacher_id: int
    teacher_name: str
    average_teacher_lesson_rate: Decimal
    visits_count: int
    completed_lessons_value: Decimal
    teacher_earned: Decimal
    school_earned: Decimal
    average_lesson_price: Decimal
    average_teacher_earning: Decimal
    share_of_total_teacher_payouts: Decimal
    last_visit_date: date | None = None
    visits: list[TeacherEarningVisit]


class FinanceSummary(ApiModel):
    memberships_sold_total: Decimal
    payments_received_total: Decimal
    completed_lessons_value: Decimal
    teacher_earnings_total: Decimal
    school_earnings_total: Decimal
    completed_visits_count: int
    average_lesson_price: Decimal
    average_teacher_earning: Decimal
    active_teachers_count: int


class DashboardData(ApiModel):
    summary: FinanceSummary
    memberships: list[MembershipRead]
    payments: list[PaymentRead]
    visits: list[VisitRead]


class TeacherEarningsQuery(ApiModel):
    date_from: date | None = None
    date_to: date | None = None
    teacher_id: int | None = None
    include_cancelled: bool = False
