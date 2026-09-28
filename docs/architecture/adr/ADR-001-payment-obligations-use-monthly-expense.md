# ADR-001: Payment obligations use MonthlyExpense as source of truth

Status: Accepted

## Context

The product has required payments and monthly financial reporting. The architecture snapshot shows payment obligations connected to monthly expense data and notifications.

## Decision

Use `MonthlyExpense` as the source of truth for required payment obligations in the current architecture snapshot. Payment obligations are represented as an operational view/process over monthly expenses rather than as a separate canonical financial source.

## Consequences

- The monthly expense module owns the payment obligation amount and schedule.
- Notifications and finance reporting consume the derived obligation state.
- If future requirements need independent payment obligation lifecycle, a new entity/table and migration must be introduced explicitly.

## References

- `sot.payment_obligations`
- `flow.monthly_expense_to_payment_obligation`
- `flow.payment_obligation_to_notifications`
