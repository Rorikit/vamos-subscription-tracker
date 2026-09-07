from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import MonthlyExpense, Operator
from app.services.finance import TEACHER_EXPENSE_CATEGORY_NAME, _effective_amount, _expense_status, ensure_monthly_expenses, get_summary, month_bounds
from app.services.lesson_finance import quantize_money


def list_payment_obligations(db: Session, year: int, month: int, status: str | None = None) -> dict:
    expenses = ensure_monthly_expenses(db, year, month)
    date_from, date_to = month_bounds(year, month)
    summary = get_summary(db, date_from=date_from, date_to=date_to)
    teacher_expense_total = quantize_money(Decimal(summary["teacher_earnings_total"]))
    items = [_serialize_obligation(expense, teacher_expense_total) for expense in expenses]
    if status:
        items = [item for item in items if item["status"] == status]
    return {
        "year": year,
        "month": month,
        "total_count": len(items),
        "unpaid_count": len([item for item in items if not item["paid"]]),
        "due_today_count": len([item for item in items if item["status"] == "due_today"]),
        "overdue_count": len([item for item in items if item["status"] == "overdue"]),
        "paid_count": len([item for item in items if item["paid"]]),
        "items": items,
    }


def list_current_payment_obligations(db: Session) -> dict:
    today = date.today()
    return list_payment_obligations(db, today.year, today.month)


def mark_payment_obligation_paid(
    db: Session,
    expense_id: int,
    operator: Operator,
    actual_amount: Decimal | None = None,
) -> MonthlyExpense:
    today = date.today()
    expense = _get_current_expense(db, expense_id, today)
    if expense.paid:
        raise HTTPException(status_code=400, detail="Платеж уже отмечен как оплаченный")

    is_teacher_expense = expense.category.name == TEACHER_EXPENSE_CATEGORY_NAME
    if expense.category.is_variable and not is_teacher_expense:
        if actual_amount is None and expense.actual_amount is None:
            raise HTTPException(status_code=400, detail="Укажите фактическую сумму для переменного расхода")
        if actual_amount is not None:
            expense.actual_amount = quantize_money(actual_amount)
    elif actual_amount is not None:
        raise HTTPException(status_code=400, detail="Для фиксированного расхода сумма не изменяется при оплате")

    expense.paid = True
    expense.paid_at = datetime.utcnow()
    expense.paid_by_user_id = operator.id
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def mark_payment_obligation_unpaid(db: Session, expense_id: int) -> MonthlyExpense:
    today = date.today()
    expense = _get_current_expense(db, expense_id, today)
    if not expense.paid:
        raise HTTPException(status_code=400, detail="Платеж еще не отмечен как оплаченный")
    expense.paid = False
    expense.paid_at = None
    expense.paid_by_user_id = None
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def _get_current_expense(db: Session, expense_id: int, today: date) -> MonthlyExpense:
    expense = db.get(MonthlyExpense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Обязательный платеж не найден")
    if expense.year != today.year or expense.month != today.month:
        raise HTTPException(status_code=400, detail="Операция доступна только для платежей текущего месяца")
    return expense


def _serialize_obligation(expense: MonthlyExpense, teacher_expense_total: Decimal) -> dict:
    display_amount = _effective_amount(expense, teacher_expense_total)
    due_day = min(expense.category.reminder_day, monthrange(expense.year, expense.month)[1])
    return {
        "id": expense.id,
        "name": expense.category.name,
        "planned_amount": quantize_money(expense.planned_amount or 0),
        "actual_amount": quantize_money(expense.actual_amount) if expense.actual_amount is not None else None,
        "display_amount": display_amount,
        "due_date": date(expense.year, expense.month, due_day),
        "reminder_day": expense.category.reminder_day,
        "paid": expense.paid,
        "paid_at": expense.paid_at.date() if expense.paid_at else None,
        "paid_by_user_id": expense.paid_by_user_id,
        "paid_by_name": expense.paid_by.full_name if expense.paid_by else None,
        "status": _expense_status(expense),
        "is_variable": expense.category.is_variable,
        "comment": expense.comment,
    }
