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
    attention_items = [
        item
        for item in obligations["items"]
        if not item["paid"] and item["status"] in {"upcoming", "due_today", "overdue"}
    ]
    if not attention_items:
        return {"items": []}

    if not (has_permission(operator, Permission.PAYMENT_OBLIGATION_VIEW) or has_permission(operator, Permission.FINANCE_VIEW)):
        return {"items": []}

    overdue_count = len([item for item in attention_items if item["status"] == "overdue"])
    due_today_count = len([item for item in attention_items if item["status"] == "due_today"])
    upcoming_count = len([item for item in attention_items if item["status"] == "upcoming"])
    severity = "error" if overdue_count else "warning" if due_today_count else "info"
    nearest_due_date = min(item["due_date"] for item in attention_items)

    amount = None
    action = "/payment-obligations"
    if has_permission(operator, Permission.FINANCE_VIEW):
        amount = quantize_money(sum((Decimal(item["display_amount"]) for item in attention_items), Decimal("0")))
        action = "/finance#reminders"

    return {
        "items": [
            {
                "type": "expense_payment_due",
                "count": len(attention_items),
                "severity": severity,
                "action": action,
                "amount": amount,
                "upcoming_count": upcoming_count,
                "due_today_count": due_today_count,
                "overdue_count": overdue_count,
                "nearest_due_date": nearest_due_date,
            }
        ]
    }
