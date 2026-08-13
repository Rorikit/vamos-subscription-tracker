from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import ExtraExpense, ExtraExpenseStatus, Operator
from app.schemas.extra_expense import ExtraExpenseCreate
from app.services.lesson_finance import quantize_money


def create_extra_expense(db: Session, payload: ExtraExpenseCreate, operator: Operator) -> ExtraExpense:
    expense = ExtraExpense(
        title=payload.title.strip(),
        amount=quantize_money(Decimal(payload.amount)),
        expense_date=payload.expense_date,
        comment=payload.comment,
        status=ExtraExpenseStatus.ACTIVE,
        created_by_user_id=operator.id,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def update_extra_expense(db: Session, expense_id: int, data: dict) -> ExtraExpense:
    expense = db.get(ExtraExpense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Внештатный расход не найден")
    if expense.status == ExtraExpenseStatus.CANCELLED:
        raise HTTPException(status_code=409, detail="Отмененный расход нельзя редактировать")
    for key, value in data.items():
        if key == "title" and value is not None:
            value = value.strip()
        if key == "amount" and value is not None:
            value = quantize_money(Decimal(value))
        setattr(expense, key, value)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def cancel_extra_expense(db: Session, expense_id: int, operator: Operator) -> ExtraExpense:
    expense = db.get(ExtraExpense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Внештатный расход не найден")
    if expense.status == ExtraExpenseStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Расход уже отменен")
    expense.status = ExtraExpenseStatus.CANCELLED
    expense.cancelled_at = datetime.utcnow()
    expense.cancelled_by_user_id = operator.id
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def list_extra_expenses(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    status_filter: ExtraExpenseStatus | None = None,
    page: int = 1,
    page_size: int = 100,
) -> list[dict]:
    query = _filtered_query(db, date_from, date_to, status_filter)
    expenses = query.order_by(ExtraExpense.expense_date.desc(), ExtraExpense.id.desc()).all()
    if search:
        needle = search.strip().casefold()
        expenses = [expense for expense in expenses if needle in expense.title.casefold()]
    page_size = min(max(page_size, 1), 200)
    offset = (max(page, 1) - 1) * page_size
    return [serialize_extra_expense(expense) for expense in expenses[offset : offset + page_size]]


def get_extra_expense_summary(db: Session, date_from: date | None = None, date_to: date | None = None) -> dict:
    query = db.query(ExtraExpense).filter(ExtraExpense.status == ExtraExpenseStatus.ACTIVE)
    query = _apply_date_range(query, date_from, date_to)
    expenses = query.all()
    total = quantize_money(sum((Decimal(expense.amount or 0) for expense in expenses), Decimal("0")))
    count = len(expenses)
    return {
        "expenses_total": total,
        "expenses_count": count,
        "average_expense": quantize_money(total / Decimal(count)) if count else Decimal("0.00"),
    }


def get_extra_expenses_total(db: Session, date_from: date | None = None, date_to: date | None = None) -> Decimal:
    query = db.query(func.coalesce(func.sum(ExtraExpense.amount), 0)).filter(ExtraExpense.status == ExtraExpenseStatus.ACTIVE)
    query = _apply_date_range(query, date_from, date_to)
    return quantize_money(Decimal(query.scalar() or 0))


def serialize_extra_expense(expense: ExtraExpense) -> dict:
    return {
        "id": expense.id,
        "title": expense.title,
        "amount": quantize_money(Decimal(expense.amount or 0)),
        "expense_date": expense.expense_date,
        "comment": expense.comment,
        "status": expense.status,
        "created_by_user_id": expense.created_by_user_id,
        "created_by_name": expense.created_by.full_name if expense.created_by else None,
        "cancelled_at": expense.cancelled_at,
        "cancelled_by_user_id": expense.cancelled_by_user_id,
        "created_at": expense.created_at,
        "updated_at": expense.updated_at,
    }


def _filtered_query(
    db: Session,
    date_from: date | None,
    date_to: date | None,
    status_filter: ExtraExpenseStatus | None,
):
    query = db.query(ExtraExpense).options(joinedload(ExtraExpense.created_by))
    query = _apply_date_range(query, date_from, date_to)
    if status_filter:
        query = query.filter(ExtraExpense.status == status_filter)
    return query


def _apply_date_range(query, date_from: date | None, date_to: date | None):
    if date_from:
        query = query.filter(ExtraExpense.expense_date >= date_from)
    if date_to:
        query = query.filter(ExtraExpense.expense_date <= date_to)
    return query
