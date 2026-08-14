from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ExtraExpense, ExtraExpenseStatus, Operator
from app.schemas.extra_expense import ExtraExpenseCreate, ExtraExpenseRead, ExtraExpenseSummary, ExtraExpenseUpdate
from app.services.audit import log_action, snapshot
from app.services.auth import get_current_operator, require_admin, require_operator_access
from app.services.extra_expenses import (
    cancel_extra_expense,
    create_extra_expense,
    delete_extra_expense,
    get_extra_expense_summary,
    list_extra_expenses,
    serialize_extra_expense,
    update_extra_expense,
)

router = APIRouter(prefix="/extra-expenses", tags=["extra-expenses"])


@router.get("", response_model=list[ExtraExpenseRead])
def list_items(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    search: str | None = Query(default=None),
    status: ExtraExpenseStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    _operator: Operator = Depends(get_current_operator),
):
    return list_extra_expenses(db, date_from, date_to, search, status, page, page_size)


@router.get("/summary", response_model=ExtraExpenseSummary)
def summary(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _operator: Operator = Depends(get_current_operator),
):
    return get_extra_expense_summary(db, date_from, date_to)


@router.post("", response_model=ExtraExpenseRead)
def create_item(payload: ExtraExpenseCreate, db: Session = Depends(get_db), operator: Operator = Depends(require_operator_access)):
    expense = create_extra_expense(db, payload, operator)
    log_action(db, operator, "extra_expense_created", "extra_expense", expense.id, expense.title, after={"amount": str(expense.amount), "date": str(expense.expense_date), "user_id": operator.id})
    return serialize_extra_expense(expense)


@router.patch("/{expense_id}", response_model=ExtraExpenseRead)
def patch_item(expense_id: int, payload: ExtraExpenseUpdate, db: Session = Depends(get_db), operator: Operator = Depends(require_operator_access)):
    current = db.get(ExtraExpense, expense_id)
    before = snapshot(current, ["title", "amount", "expense_date", "comment", "status"]) if current else None
    expense = update_extra_expense(db, expense_id, payload.model_dump(exclude_unset=True))
    log_action(db, operator, "extra_expense_updated", "extra_expense", expense.id, expense.title, before=before, after={"amount": str(expense.amount), "date": str(expense.expense_date), "user_id": operator.id})
    return serialize_extra_expense(expense)


@router.post("/{expense_id}/cancel", response_model=ExtraExpenseRead)
def cancel_item(expense_id: int, db: Session = Depends(get_db), operator: Operator = Depends(require_operator_access)):
    expense = cancel_extra_expense(db, expense_id, operator)
    log_action(db, operator, "extra_expense_cancelled", "extra_expense", expense.id, expense.title, after={"amount": str(expense.amount), "date": str(expense.expense_date), "user_id": operator.id})
    return serialize_extra_expense(expense)


@router.delete("/{expense_id}", status_code=204)
def delete_item(expense_id: int, db: Session = Depends(get_db), operator: Operator = Depends(require_admin)):
    current = db.get(ExtraExpense, expense_id)
    before = snapshot(current, ["title", "amount", "expense_date", "comment", "status"]) if current else None
    label = current.title if current else None
    delete_extra_expense(db, expense_id)
    log_action(db, operator, "extra_expense_deleted", "extra_expense", expense_id, label, before=before)
    return None
