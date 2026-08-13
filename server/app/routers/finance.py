from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Membership, MonthlyExpense, Operator, Visit
from app.schemas.finance import FinanceMonthlyReport, FinanceSummary, MonthlyExpenseRead, MonthlyExpenseUpdate, ReminderStatus, TeacherEarning
from app.schemas.visit import VisitRead
from app.services.audit import log_action, snapshot
from app.services.auth import require_finance_access
from app.services.finance import get_monthly_report, get_reminder_status, get_summary, get_teacher_earnings, list_monthly_expenses, mark_expense_paid, mark_expense_unpaid, update_monthly_expense

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/summary", response_model=FinanceSummary)
def summary(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    teacher_id: int | None = Query(default=None),
    membership_type_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _operator=Depends(require_finance_access),
):
    return get_summary(db, date_from=date_from, date_to=date_to, teacher_id=teacher_id, membership_type_id=membership_type_id)


@router.get("/teacher-earnings", response_model=list[TeacherEarning])
def teacher_earnings(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    teacher_id: int | None = Query(default=None),
    membership_type_id: int | None = Query(default=None),
    include_cancelled: bool = Query(default=False),
    db: Session = Depends(get_db),
    _operator=Depends(require_finance_access),
):
    return get_teacher_earnings(db, date_from=date_from, date_to=date_to, teacher_id=teacher_id, membership_type_id=membership_type_id, include_cancelled=include_cancelled)


@router.get("/monthly-report", response_model=FinanceMonthlyReport)
def monthly_report(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    _operator: Operator = Depends(require_finance_access),
):
    return get_monthly_report(db, year, month)


@router.get("/expenses", response_model=list[MonthlyExpenseRead])
def expenses(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    _operator: Operator = Depends(require_finance_access),
):
    return list_monthly_expenses(db, year, month)


@router.patch("/expenses/{expense_id}", response_model=MonthlyExpenseRead)
def patch_expense(
    expense_id: int,
    payload: MonthlyExpenseUpdate,
    db: Session = Depends(get_db),
    operator: Operator = Depends(require_finance_access),
):
    current = db.get(MonthlyExpense, expense_id)
    before = snapshot(current, ["planned_amount", "actual_amount", "comment"]) if current else None
    expense = update_monthly_expense(db, expense_id, payload.model_dump(exclude_unset=True))
    log_action(db, operator, "expense_amount_changed", "monthly_expense", expense.id, expense.category.name if expense.category else None, before=before, after=snapshot(expense, ["planned_amount", "actual_amount", "comment"]))
    report = get_monthly_report(db, expense.year, expense.month)
    return next(item for item in report["expenses"] if item["id"] == expense.id)


@router.post("/expenses/{expense_id}/pay", response_model=MonthlyExpenseRead)
def pay_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    operator: Operator = Depends(require_finance_access),
):
    expense = mark_expense_paid(db, expense_id, operator)
    log_action(db, operator, "expense_paid", "monthly_expense", expense.id, expense.category.name if expense.category else None, after=snapshot(expense, ["paid", "paid_at", "paid_by_user_id"]))
    report = get_monthly_report(db, expense.year, expense.month)
    return next(item for item in report["expenses"] if item["id"] == expense.id)


@router.post("/expenses/{expense_id}/unpay", response_model=MonthlyExpenseRead)
def unpay_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    operator: Operator = Depends(require_finance_access),
):
    expense = mark_expense_unpaid(db, expense_id)
    log_action(db, operator, "expense_unpaid", "monthly_expense", expense.id, expense.category.name if expense.category else None, after=snapshot(expense, ["paid", "paid_at", "paid_by_user_id"]))
    report = get_monthly_report(db, expense.year, expense.month)
    return next(item for item in report["expenses"] if item["id"] == expense.id)


@router.get("/reminders/status", response_model=ReminderStatus)
def reminders_status(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _operator: Operator = Depends(require_finance_access),
):
    return get_reminder_status(db, year, month)


@router.get("/reminders", response_model=list[MonthlyExpenseRead])
def reminders(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _operator: Operator = Depends(require_finance_access),
):
    today = date.today()
    report = get_monthly_report(db, year or today.year, month or today.month)
    return [expense for expense in report["expenses"] if not expense["paid"] and expense["status"] in {"due_today", "overdue"}]


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    from app.services.memberships import serialize_membership

    memberships = (
        db.query(Membership)
        .options(joinedload(Membership.participant), joinedload(Membership.membership_type))
        .order_by(Membership.end_date)
        .all()
    )
    recent_visits = (
        db.query(Visit)
        .options(
            joinedload(Visit.participant),
            joinedload(Visit.teacher),
            joinedload(Visit.membership).joinedload(Membership.membership_type),
        )
        .order_by(Visit.visit_date.desc(), Visit.id.desc())
        .limit(8)
        .all()
    )
    return {
        "summary": get_summary(db),
        "memberships": [serialize_membership(db, membership) for membership in memberships],
        "visits": recent_visits,
    }
