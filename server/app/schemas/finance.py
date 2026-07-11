from datetime import date
from decimal import Decimal

from app.schemas.common import ApiModel
from app.schemas.membership import MembershipRead
from app.schemas.payment import PaymentRead
from app.schemas.visit import VisitRead


class TeacherEarning(ApiModel):
    teacher_id: int
    teacher_name: str
    visits_count: int
    total_earned: Decimal
    average_lesson_price: Decimal
    visits: list["TeacherEarningVisit"]


class TeacherEarningVisit(ApiModel):
    visit_id: int
    visit_date: date
    participant_id: int
    participant_name: str
    membership_id: int
    membership_name: str
    lesson_price: Decimal
    is_cancelled: bool


class FinanceSummary(ApiModel):
    total_revenue: Decimal
    total_visits: int
    teacher_earnings_total: Decimal
    teacher_earnings: list[TeacherEarning]


class DashboardData(ApiModel):
    summary: FinanceSummary
    memberships: list[MembershipRead]
    payments: list[PaymentRead]
    visits: list[VisitRead]


class TeacherEarningsQuery(ApiModel):
    date_from: date | None = None
    date_to: date | None = None
    teacher_id: int | None = None
