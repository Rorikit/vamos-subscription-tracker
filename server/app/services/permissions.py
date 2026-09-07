from enum import Enum

from fastapi import HTTPException, status

from app.models.operator import Operator, OperatorRole


class Permission(str, Enum):
    FINANCE_VIEW = "finance.view"
    FINANCE_MANAGE = "finance.manage"
    PAYMENT_OBLIGATION_VIEW = "payment_obligation.view"
    PAYMENT_OBLIGATION_MARK_PAID = "payment_obligation.mark_paid"
    PAYMENT_OBLIGATION_UNPAY = "payment_obligation.unpay"


ROLE_PERMISSIONS: dict[OperatorRole, set[Permission]] = {
    OperatorRole.ADMIN: {
        Permission.FINANCE_VIEW,
        Permission.FINANCE_MANAGE,
        Permission.PAYMENT_OBLIGATION_VIEW,
        Permission.PAYMENT_OBLIGATION_MARK_PAID,
        Permission.PAYMENT_OBLIGATION_UNPAY,
    },
    OperatorRole.FINANCE: {
        Permission.FINANCE_VIEW,
        Permission.FINANCE_MANAGE,
    },
    OperatorRole.OPERATOR: {
        Permission.PAYMENT_OBLIGATION_VIEW,
        Permission.PAYMENT_OBLIGATION_MARK_PAID,
        Permission.PAYMENT_OBLIGATION_UNPAY,
    },
}


def has_permission(operator: Operator, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(operator.role, set())


def require_permission(operator: Operator, permission: Permission, detail: str = "Недостаточно прав") -> Operator:
    if not has_permission(operator, permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    return operator
