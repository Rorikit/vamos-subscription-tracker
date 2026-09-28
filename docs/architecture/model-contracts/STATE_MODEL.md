# Model Contract: State Model

Purpose: render entity lifecycles and valid transitions without mixing persisted state, derived state and operational status.

Required snapshot sections:

- `entities`
- `states`
- `transitions`
- `stateful_entities`
- `derived_state_groups`
- `business_rules`

Required fields:

- State: `id`, `entity`, `value`, `name_ru`
- Transition: `id`, `entity`, `from`, `to`, `trigger`, `business_rule`

Validation:

- state belongs to exactly one entity;
- transition cannot cross entity state machines;
- `PERSISTED_STATE` must reference a real persisted entity field;
- `DERIVED_STATE` must describe a structural expression or boolean representation;
- `OPERATIONAL_STATUS` belongs to derived state groups, not persisted enum machines;
- role fields are permissions/RBAC, not lifecycle states;
- one entity should be rendered as one state machine.
- transition trigger should be tied to a rule or product action.
