# State Modeling

Canonical State Model отвечает на вопрос:

```text
Какие реальные состояния есть у domain entity, как она между ними переходит,
кто инициирует переход, при каких условиях и какие последствия это вызывает?
```

Модель не строит красивую полную матрицу переходов. Если переход не подтвержден кодом, бизнес-правилом или API, его нет в canonical model.

## State Kinds

### PERSISTED_STATE

Состояние хранится в поле entity.

Примеры:

- `Membership.status`
- `ScheduleEvent.status`
- `PracticeRental.status`
- `ExtraExpense.status`

### DERIVED_STATE

Состояние вычисляется из boolean-поля или нескольких persisted-полей.

Примеры:

- `Visit.active/cancelled` из `is_cancelled`
- `MonthlyExpense.unpaid/paid` из `paid`
- `Membership.currently_active` из `status`, `remaining_lessons`, `end_date`

### OPERATIONAL_STATUS

Статус нужен UI/use-case, но не является самостоятельным persisted lifecycle.

Пример:

- `MonthlyExpense`: `pending`, `due_today`, `overdue`, `paid`

Эти статусы зависят от `paid`, `reminder_day` и текущей даты, поэтому хранятся как `derived_state_group`, а не как states persisted machine.

## Transition

Transition описывает подтвержденный переход между состояниями одной entity.

Transition содержит:

- `id`
- `entity`
- `from`
- `to`
- `trigger`
- `trigger_type`
- `transition_kind`
- `guard`
- `execution`
- `caused_by`
- `business_rule`
- `service`
- `api`
- `side_effects`
- `evidence`

## Trigger Types

- `API_ACTION`
- `BUSINESS_RULE`
- `TIME_BASED`
- `SYSTEM_ACTION`
- `USER_ACTION`

## Transition Kinds

- `NORMAL` - обычный переход.
- `MANUAL` - явное действие оператора.
- `AUTOMATIC` - переход выполняется бизнес-правилом.
- `COMPENSATING` - компенсация или откат ранее выполненного действия.

## Guards

Guard добавляется только при evidence.

Примеры:

- `remaining_lessons == 0 and status == active`
- `status == active and end_date < today`
- `visit exists and is_cancelled == false`

## Lazy Time Transition

`Membership active -> expired` является time-based, но выполняется lazy evaluation при lookup/serialization.

Это не cron и не background scheduler.

## Compensation

Компенсирующие переходы сохраняют side effects.

Пример:

`ScheduleEvent completed -> cancelled`:

- linked Visit cancelled
- Membership lesson restored
- attendance updated

## Current Stateful Entities

- `entity.membership` - READY
- `entity.schedule_event` - READY
- `entity.schedule_event_participant` - READY
- `entity.practice_rental` - READY
- `entity.extra_expense` - READY
- `entity.visit` - READY
- `entity.monthly_expense` - READY
- `entity.operator` - NOT_STATEFUL

`Operator.role` относится к RBAC, а не к lifecycle state.
