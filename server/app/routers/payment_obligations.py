from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Operator
from app.schemas.payment_obligation import PaymentObligationPay, PaymentObligationRead, PaymentObligationSummary
from app.services.audit import log_action, snapshot
from app.services.auth import get_current_operator
from app.services.payment_obligations import list_current_payment_obligations, list_payment_obligations, mark_payment_obligation_paid, mark_payment_obligation_unpaid
from app.services.permissions import Permission, require_permission

router = APIRouter(prefix="/payment-obligations", tags=["payment-obligations"])


def require_obligation_view(operator: Operator = Depends(get_current_operator)) -> Operator:
    return require_permission(operator, Permission.PAYMENT_OBLIGATION_VIEW, "Недостаточно прав для обязательных платежей")


def require_obligation_mark_paid(operator: Operator = Depends(get_current_operator)) -> Operator:
    return require_permission(operator, Permission.PAYMENT_OBLIGATION_MARK_PAID, "Недостаточно прав для оплаты обязательных платежей")


def require_obligation_unpay(operator: Operator = Depends(get_current_operator)) -> Operator:
    return require_permission(operator, Permission.PAYMENT_OBLIGATION_UNPAY, "Недостаточно прав для отмены оплаты")


@router.get("/current", response_model=PaymentObligationSummary)
def current_obligations(
    db: Session = Depends(get_db),
    _operator: Operator = Depends(require_obligation_view),
):
    return list_current_payment_obligations(db)


@router.get("", response_model=PaymentObligationSummary)
def obligations(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _operator: Operator = Depends(require_obligation_view),
):
    today = date.today()
    return list_payment_obligations(db, year or today.year, month or today.month, status=status)


@router.post("/{expense_id}/pay", response_model=PaymentObligationRead)
def pay_obligation(
    expense_id: int,
    payload: PaymentObligationPay | None = None,
    db: Session = Depends(get_db),
    operator: Operator = Depends(require_obligation_mark_paid),
):
    expense = mark_payment_obligation_paid(db, expense_id, operator, Decimal(payload.actual_amount) if payload and payload.actual_amount is not None else None)
    log_action(
        db,
        operator,
        "payment_obligation_paid",
        "monthly_expense",
        expense.id,
        expense.category.name if expense.category else None,
        after=snapshot(expense, ["actual_amount", "paid", "paid_at", "paid_by_user_id"]),
    )
    summary = list_payment_obligations(db, expense.year, expense.month)
    return next(item for item in summary["items"] if item["id"] == expense.id)


@router.post("/{expense_id}/unpay", response_model=PaymentObligationRead)
def unpay_obligation(
    expense_id: int,
    db: Session = Depends(get_db),
    operator: Operator = Depends(require_obligation_unpay),
):
    expense = mark_payment_obligation_unpaid(db, expense_id)
    log_action(
        db,
        operator,
        "payment_obligation_unpaid",
        "monthly_expense",
        expense.id,
        expense.category.name if expense.category else None,
        after=snapshot(expense, ["paid", "paid_at", "paid_by_user_id"]),
    )
    summary = list_payment_obligations(db, expense.year, expense.month)
    return next(item for item in summary["items"] if item["id"] == expense.id)
