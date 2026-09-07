from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Operator
from app.services.lesson_finance import quantize_money
from app.services.payment_obligations import list_payment_obligations
from app.services.permissions import Permission, has_permission


def get_notification_summary(db: Session, operator: Operator) -> dict:
    today = date.today()
    obligations = list_payment_obligations(db, today.year, today.month)
    due_items = [item for item in obligations["items"] if not item["paid"] and item["status"] in {"due_today", "overdue"}]
    if not due_items:
        return {"items": []}

    if not (has_permission(operator, Permission.PAYMENT_OBLIGATION_VIEW) or has_permission(operator, Permission.FINANCE_VIEW)):
        return {"items": []}

    amount = None
    action = "/payment-obligations"
    if has_permission(operator, Permission.FINANCE_VIEW):
        amount = quantize_money(sum((Decimal(item["display_amount"]) for item in due_items), Decimal("0")))
        action = "/finance#reminders"

    return {
        "items": [
            {
                "type": "expense_payment_due",
                "count": len(due_items),
                "severity": "warning",
                "action": action,
                "amount": amount,
            }
        ]
    }
