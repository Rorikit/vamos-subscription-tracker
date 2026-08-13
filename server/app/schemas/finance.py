from datetime import date
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.schemas.common import ApiModel
from app.schemas.membership import MembershipRead
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
    last_visit_date: date | None = None
    visits: list[TeacherEarningVisit]


class FinanceSummary(ApiModel):
    memberships_sold_total: Decimal
    completed_lessons_value: Decimal
    teacher_earnings_total: Decimal
    school_earnings_total: Decimal
    completed_visits_count: int
    average_lesson_price: Decimal
    average_teacher_earning: Decimal
    active_teachers_count: int


class ExpenseCategoryRead(ApiModel):
    id: int
    name: str
    default_amount: Decimal | None = None
    is_variable: bool
    is_active: bool
    reminder_day: int
    sort_order: int


class ExpenseCategoryCreate(BaseModel):
    name: str
    default_amount: Decimal | None = None
    is_variable: bool = False
    is_active: bool = True
    reminder_day: int = 26
    sort_order: int = 100

    @field_validator("reminder_day")
    @classmethod
    def validate_reminder_day(cls, value: int) -> int:
        if value < 1 or value > 31:
            raise ValueError("reminder_day must be between 1 and 31")
        return value


class ExpenseCategoryUpdate(BaseModel):
    name: str | None = None
    default_amount: Decimal | None = None
    is_variable: bool | None = None
    is_active: bool | None = None
    reminder_day: int | None = None
    sort_order: int | None = None

    @field_validator("reminder_day")
    @classmethod
    def validate_reminder_day(cls, value: int | None) -> int | None:
        if value is not None and (value < 1 or value > 31):
            raise ValueError("reminder_day must be between 1 and 31")
        return value


class MonthlyExpenseRead(ApiModel):
    id: int
    category_id: int
    category_name: str
    year: int
    month: int
    planned_amount: Decimal
    actual_amount: Decimal | None
    effective_amount: Decimal
    paid: bool
    paid_at: date | None = None
    paid_by_user_id: int | None = None
    paid_by_name: str | None = None
    comment: str | None = None
    is_variable: bool
    reminder_day: int
    status: str
    is_teacher_expense: bool = False


class MonthlyExpenseUpdate(BaseModel):
    planned_amount: Decimal | None = None
    actual_amount: Decimal | None = None
    comment: str | None = None


class ExpenseChartItem(ApiModel):
    category_id: int
    category_name: str
    amount: Decimal
    percentage: Decimal
    is_teacher_expense: bool = False


class FinanceMonthlyReport(ApiModel):
    year: int
    month: int
    date_from: date
    date_to: date
    income_total: Decimal
    memberships_sold_total: Decimal
    expenses_total: Decimal
    teacher_expense_total: Decimal
    net_result: Decimal
    unpaid_expenses_count: int
    unpaid_expenses_total: Decimal
    completed_visits_count: int
    chart: list[ExpenseChartItem]
    expenses: list[MonthlyExpenseRead]
    teacher_earnings: list[TeacherEarning]


class ReminderStatus(ApiModel):
    year: int
    month: int
    active: bool
    unpaid_count: int
    unpaid_total: Decimal


class DashboardData(ApiModel):
    summary: FinanceSummary
    memberships: list[MembershipRead]
    visits: list[VisitRead]


class TeacherEarningsQuery(ApiModel):
    date_from: date | None = None
    date_to: date | None = None
    teacher_id: int | None = None
    include_cancelled: bool = False
