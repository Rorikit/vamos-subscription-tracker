from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


SNAPSHOT_PATH = Path(__file__).with_name("architecture_snapshot.json")

STATE_KINDS = {"PERSISTED_STATE", "DERIVED_STATE", "OPERATIONAL_STATUS"}
TRANSITION_KINDS = {"NORMAL", "COMPENSATING", "AUTOMATIC", "MANUAL"}
TRIGGER_TYPES = {"API_ACTION", "BUSINESS_RULE", "TIME_BASED", "SYSTEM_ACTION", "USER_ACTION"}


STATEFUL_ENTITY_SPECS = [
    {
        "entity": "entity.membership",
        "lifecycle_type": "PERSISTED_ENUM",
        "state_kind": "PERSISTED_STATE",
        "field": "status",
        "states": ["active", "finished", "expired", "frozen", "cancelled"],
        "status": "READY",
    },
    {
        "entity": "entity.schedule_event",
        "lifecycle_type": "PERSISTED_STRING_ENUM",
        "state_kind": "PERSISTED_STATE",
        "field": "status",
        "states": ["scheduled", "completed", "cancelled"],
        "status": "READY",
    },
    {
        "entity": "entity.schedule_event_participant",
        "lifecycle_type": "PERSISTED_STRING_ENUM",
        "state_kind": "PERSISTED_STATE",
        "field": "attendance_status",
        "states": ["planned", "attended", "absent", "cancelled", "refunded"],
        "status": "READY",
    },
    {
        "entity": "entity.practice_rental",
        "lifecycle_type": "PERSISTED_ENUM",
        "state_kind": "PERSISTED_STATE",
        "field": "status",
        "states": ["active", "cancelled"],
        "status": "READY",
    },
    {
        "entity": "entity.extra_expense",
        "lifecycle_type": "PERSISTED_ENUM",
        "state_kind": "PERSISTED_STATE",
        "field": "status",
        "states": ["active", "cancelled"],
        "status": "READY",
    },
    {
        "entity": "entity.visit",
        "lifecycle_type": "BOOLEAN_LIFECYCLE",
        "state_kind": "DERIVED_STATE",
        "field": "is_cancelled",
        "states": ["active", "cancelled"],
        "status": "READY",
    },
    {
        "entity": "entity.monthly_expense",
        "lifecycle_type": "BOOLEAN_LIFECYCLE_WITH_DERIVED_PROJECTION",
        "state_kind": "DERIVED_STATE",
        "field": "paid",
        "states": ["unpaid", "paid"],
        "status": "READY",
    },
    {
        "entity": "entity.operator",
        "lifecycle_type": "NOT_STATEFUL",
        "field": "is_active",
        "states": [],
        "status": "NOT_STATEFUL",
        "reason": "Operator.role is RBAC, not lifecycle state. is_active has no evidenced deactivation/reactivation lifecycle in the canonical model.",
    },
]


TRANSITION_SPECS = [
    {
        "id": "transition.membership.active_to_finished",
        "entity": "entity.membership",
        "from": "active",
        "to": "finished",
        "trigger": "remaining_lessons reaches 0 during lesson write-off",
        "trigger_type": "BUSINESS_RULE",
        "transition_kind": "AUTOMATIC",
        "guard": "remaining_lessons == 0 and status == active",
        "caused_by": ["rule.membership.complete_when_empty", "service.memberships"],
        "api": ["api.schedule.complete"],
    },
    {
        "id": "transition.membership.active_to_expired",
        "entity": "entity.membership",
        "from": "active",
        "to": "expired",
        "trigger": "membership is looked up or serialized after end_date",
        "trigger_type": "TIME_BASED",
        "transition_kind": "AUTOMATIC",
        "execution": "lazy evaluation",
        "guard": "status == active and end_date < today",
        "caused_by": ["rule.membership.expire_refresh", "service.memberships"],
        "api": ["api.memberships.list", "api.memberships.get"],
    },
    {
        "id": "transition.membership.active_to_frozen",
        "entity": "entity.membership",
        "from": "active",
        "to": "frozen",
        "trigger": "membership freeze action",
        "trigger_type": "API_ACTION",
        "transition_kind": "MANUAL",
        "caused_by": ["service.memberships"],
        "api": ["api.memberships.freeze"],
    },
    {
        "id": "transition.membership.frozen_to_active",
        "entity": "entity.membership",
        "from": "frozen",
        "to": "active",
        "trigger": "membership unfreeze action",
        "trigger_type": "API_ACTION",
        "transition_kind": "MANUAL",
        "caused_by": ["service.memberships"],
        "api": ["api.memberships.unfreeze"],
    },
    {
        "id": "transition.membership.active_to_cancelled",
        "entity": "entity.membership",
        "from": "active",
        "to": "cancelled",
        "trigger": "membership cancel action",
        "trigger_type": "API_ACTION",
        "transition_kind": "MANUAL",
        "caused_by": ["service.memberships"],
        "api": ["api.memberships.cancel"],
    },
    {
        "id": "transition.schedule_event.scheduled_to_completed",
        "entity": "entity.schedule_event",
        "from": "scheduled",
        "to": "completed",
        "trigger": "operator marks scheduled event completed",
        "trigger_type": "API_ACTION",
        "transition_kind": "MANUAL",
        "caused_by": ["rule.schedule.complete_creates_visits", "service.schedule_events"],
        "api": ["api.schedule.complete"],
        "side_effects": ["Visit records created for attended participants", "Membership lessons decremented", "attendance_status updated"],
    },
    {
        "id": "transition.schedule_event.scheduled_to_cancelled",
        "entity": "entity.schedule_event",
        "from": "scheduled",
        "to": "cancelled",
        "trigger": "operator cancels scheduled event",
        "trigger_type": "API_ACTION",
        "transition_kind": "MANUAL",
        "caused_by": ["service.schedule_events"],
        "api": ["api.schedule.cancel"],
    },
    {
        "id": "transition.schedule_event.completed_to_cancelled",
        "entity": "entity.schedule_event",
        "from": "completed",
        "to": "cancelled",
        "trigger": "operator cancels completed event",
        "trigger_type": "API_ACTION",
        "transition_kind": "COMPENSATING",
        "guard": "event.status == completed",
        "caused_by": ["rule.schedule.cancel_completed_returns_visits", "service.schedule_events"],
        "api": ["api.schedule.cancel"],
        "side_effects": ["linked Visit cancelled", "Membership lesson restored", "attendance updated"],
    },
    {
        "id": "transition.schedule_participant.planned_to_attended",
        "entity": "entity.schedule_event_participant",
        "from": "planned",
        "to": "attended",
        "trigger": "attendance decision during event completion",
        "trigger_type": "USER_ACTION",
        "transition_kind": "NORMAL",
        "caused_by": ["rule.schedule.complete_creates_visits", "service.schedule_events"],
        "api": ["api.schedule.complete"],
    },
    {
        "id": "transition.schedule_participant.planned_to_absent",
        "entity": "entity.schedule_event_participant",
        "from": "planned",
        "to": "absent",
        "trigger": "attendance decision during event completion",
        "trigger_type": "USER_ACTION",
        "transition_kind": "NORMAL",
        "caused_by": ["service.schedule_events"],
        "api": ["api.schedule.complete"],
    },
    {
        "id": "transition.schedule_participant.planned_to_cancelled",
        "entity": "entity.schedule_event_participant",
        "from": "planned",
        "to": "cancelled",
        "trigger": "event or participant cancellation before attendance",
        "trigger_type": "API_ACTION",
        "transition_kind": "MANUAL",
        "caused_by": ["service.schedule_events"],
        "api": ["api.schedule.cancel", "api.schedule.remove_participant"],
    },
    {
        "id": "transition.schedule_participant.attended_to_refunded",
        "entity": "entity.schedule_event_participant",
        "from": "attended",
        "to": "refunded",
        "trigger": "operator returns participant lesson",
        "trigger_type": "API_ACTION",
        "transition_kind": "COMPENSATING",
        "caused_by": ["rule.visit.return_restores_membership", "service.schedule_events", "service.memberships"],
        "api": ["api.schedule.return_participant"],
        "side_effects": ["linked Visit cancelled", "Membership lesson restored"],
    },
    {
        "id": "transition.practice_rental.active_to_cancelled",
        "entity": "entity.practice_rental",
        "from": "active",
        "to": "cancelled",
        "trigger": "practice rental cancel action",
        "trigger_type": "API_ACTION",
        "transition_kind": "MANUAL",
        "caused_by": ["service.practice"],
        "api": ["api.practice_rentals.cancel"],
    },
    {
        "id": "transition.extra_expense.active_to_cancelled",
        "entity": "entity.extra_expense",
        "from": "active",
        "to": "cancelled",
        "trigger": "extra expense cancel action",
        "trigger_type": "API_ACTION",
        "transition_kind": "MANUAL",
        "caused_by": ["service.extra_expenses"],
        "api": ["api.extra_expenses.cancel"],
    },
    {
        "id": "transition.visit.active_to_cancelled",
        "entity": "entity.visit",
        "from": "active",
        "to": "cancelled",
        "trigger": "visit return/cancel action",
        "trigger_type": "API_ACTION",
        "transition_kind": "COMPENSATING",
        "guard": "visit exists and is_cancelled == false",
        "caused_by": ["rule.visit.return_once", "rule.visit.return_restores_membership", "service.memberships"],
        "api": ["api.visits.cancel", "api.schedule.return_participant", "api.schedule.cancel"],
        "side_effects": ["Membership lesson restored", "teacher earning removed from finance aggregates"],
    },
    {
        "id": "transition.monthly_expense.unpaid_to_paid",
        "entity": "entity.monthly_expense",
        "from": "unpaid",
        "to": "paid",
        "trigger": "mandatory payment marked paid",
        "trigger_type": "API_ACTION",
        "transition_kind": "MANUAL",
        "caused_by": ["service.payment_obligations"],
        "api": ["api.payment_obligations.pay", "api.finance.expense_pay"],
    },
    {
        "id": "transition.monthly_expense.paid_to_unpaid",
        "entity": "entity.monthly_expense",
        "from": "paid",
        "to": "unpaid",
        "trigger": "mandatory payment unpay action",
        "trigger_type": "API_ACTION",
        "transition_kind": "COMPENSATING",
        "caused_by": ["service.payment_obligations"],
        "api": ["api.payment_obligations.unpay", "api.finance.expense_unpay"],
    },
]


DERIVED_STATE_GROUPS = [
    {
        "id": "derived_state_group.membership_current_activity",
        "entity": "entity.membership",
        "name": "Membership current activity",
        "state_kind": "DERIVED_STATE",
        "states": ["currently_active", "not_currently_active"],
        "source": ["rule.membership.active_definition", "service.memberships"],
        "expression": "status == active AND remaining_lessons > 0 AND end_date >= today",
        "source_type": "EXTRACTED",
        "confidence": "high",
    },
    {
        "id": "derived_state_group.monthly_expense_obligation_status",
        "entity": "entity.monthly_expense",
        "name": "Monthly expense obligation status",
        "state_kind": "OPERATIONAL_STATUS",
        "states": ["pending", "due_today", "overdue", "paid"],
        "source": ["service.payment_obligations", "service.notifications"],
        "expression": "paid + reminder_day + current_date",
        "source_type": "DERIVED",
        "confidence": "medium",
    },
]


def apply_state_model(snapshot: dict[str, Any]) -> dict[str, Any]:
    context = build_context(snapshot)
    stateful_entities = build_stateful_entities(snapshot, context)
    states = build_canonical_states(snapshot, context)
    transitions = build_canonical_transitions(snapshot, context, states)

    snapshot["stateful_entities"] = stateful_entities
    snapshot["states"] = states
    snapshot["transitions"] = transitions
    snapshot["derived_state_groups"] = build_derived_state_groups(context)
    snapshot["state_model_metrics"] = build_state_metrics(stateful_entities, states, transitions)
    return snapshot


def build_context(snapshot: dict[str, Any]) -> dict[str, Any]:
    ids = {}
    for section in ["entities", "business_rules", "services", "api", "use_cases", "business_processes", "data_flows"]:
        for item in snapshot.get(section, []) or []:
            ids[item["id"]] = item
    return {"ids": ids, "entities": {item["id"]: item for item in snapshot.get("entities", []) or []}}


def build_stateful_entities(snapshot: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    existing_entities = context["entities"]
    for spec in STATEFUL_ENTITY_SPECS:
        entity_id = spec["entity"]
        if entity_id not in existing_entities:
            continue
        states_count = len(spec.get("states", []))
        transition_count = sum(1 for item in TRANSITION_SPECS if item["entity"] == entity_id)
        result.append(
            {
                "id": f"stateful.{entity_id.replace('entity.', '')}",
                "entity": entity_id,
                "lifecycle_type": spec["lifecycle_type"],
                "state_kind": spec.get("state_kind"),
                "representation_field": spec.get("field"),
                "status": spec["status"],
                "states_count": states_count,
                "transitions_count": transition_count,
                "reason": spec.get("reason", "Lifecycle is backed by persisted fields or documented derived state projection."),
                "source_type": "DERIVED",
                "confidence": "high",
                "evidence": entity_evidence(existing_entities[entity_id]),
            }
        )
    return sorted(result, key=lambda item: item["id"])


def build_canonical_states(snapshot: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    states = []
    for spec in STATEFUL_ENTITY_SPECS:
        entity = context["entities"].get(spec["entity"])
        if not entity or spec["lifecycle_type"] == "NOT_STATEFUL":
            continue
        for state_name in spec["states"]:
            representation = state_representation(spec, state_name)
            states.append(
                {
                    "id": state_id(spec["entity"], state_name),
                    "entity": spec["entity"],
                    "name": state_name,
                    "state_kind": spec["state_kind"],
                    "representation": representation,
                    "source_type": "EXTRACTED" if spec["state_kind"] == "PERSISTED_STATE" else "DERIVED",
                    "confidence": "high",
                    "evidence": entity_evidence(entity),
                }
            )
    return sorted(states, key=lambda item: item["id"])


def state_representation(spec: dict[str, Any], state_name: str) -> dict[str, Any]:
    field = spec["field"]
    if spec["lifecycle_type"] == "BOOLEAN_LIFECYCLE":
        return {"field": field, "condition": "true" if state_name in {"cancelled", "paid"} else "false"}
    if spec["lifecycle_type"] == "BOOLEAN_LIFECYCLE_WITH_DERIVED_PROJECTION":
        return {"field": field, "condition": "true" if state_name == "paid" else "false"}
    return {"field": field, "value": state_name}


def build_canonical_transitions(snapshot: dict[str, Any], context: dict[str, Any], states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing_states = {item["id"] for item in states}
    transitions = []
    for spec in TRANSITION_SPECS:
        from_state = state_id(spec["entity"], spec["from"])
        to_state = state_id(spec["entity"], spec["to"])
        if from_state not in existing_states or to_state not in existing_states:
            continue
        caused_by = [ref for ref in spec.get("caused_by", []) if ref in context["ids"]]
        api_refs = [ref for ref in spec.get("api", []) if ref in context["ids"]]
        transitions.append(
            {
                "id": spec["id"],
                "entity": spec["entity"],
                "from": from_state,
                "to": to_state,
                "trigger": spec["trigger"],
                "trigger_type": spec["trigger_type"],
                "transition_kind": spec["transition_kind"],
                "guard": spec.get("guard"),
                "execution": spec.get("execution", "immediate"),
                "caused_by": caused_by,
                "business_rule": next((ref for ref in caused_by if ref.startswith("rule.")), None),
                "service": next((ref for ref in caused_by if ref.startswith("service.")), None),
                "api": api_refs,
                "side_effects": spec.get("side_effects", []),
                "source_type": "EXTRACTED",
                "confidence": "high",
                "evidence": merge_evidence([context["ids"].get(ref) for ref in [*caused_by, *api_refs] if context["ids"].get(ref)]),
            }
        )
    return sorted(transitions, key=lambda item: item["id"])


def build_derived_state_groups(context: dict[str, Any]) -> list[dict[str, Any]]:
    groups = []
    for group in DERIVED_STATE_GROUPS:
        refs = [ref for ref in group.get("source", []) if ref in context["ids"]]
        item = dict(group)
        item["source"] = refs
        item["evidence"] = merge_evidence([context["ids"].get(ref) for ref in refs if context["ids"].get(ref)])
        groups.append(item)
    return groups


def build_state_metrics(stateful_entities: list[dict[str, Any]], states: list[dict[str, Any]], transitions: list[dict[str, Any]]) -> dict[str, Any]:
    lifecycle_entities = [item for item in stateful_entities if item["status"] != "NOT_STATEFUL"]
    ready = [item for item in lifecycle_entities if item["status"] == "READY" and item["states_count"] > 0 and item["transitions_count"] > 0]
    by_entity = defaultdict(lambda: {"states": 0, "transitions": 0})
    for state in states:
        by_entity[state["entity"]]["states"] += 1
    for transition in transitions:
        by_entity[transition["entity"]]["transitions"] += 1
    return {
        "stateful_entity_count": len(stateful_entities),
        "lifecycle_entity_count": len(lifecycle_entities),
        "not_stateful_count": len(stateful_entities) - len(lifecycle_entities),
        "ready_lifecycle_entity_count": len(ready),
        "state_count": len(states),
        "transition_count": len(transitions),
        "persisted_state_count": sum(1 for item in states if item["state_kind"] == "PERSISTED_STATE"),
        "derived_state_count": sum(1 for item in states if item["state_kind"] == "DERIVED_STATE"),
        "compensating_transition_count": sum(1 for item in transitions if item["transition_kind"] == "COMPENSATING"),
        "lazy_time_transition_count": sum(1 for item in transitions if item.get("execution") == "lazy evaluation"),
        "coverage_by_entity": dict(sorted(by_entity.items())),
    }


def state_id(entity_id: str, state_name: str) -> str:
    return f"state.{entity_id.replace('entity.', '')}.{state_name}"


def entity_evidence(entity: dict[str, Any]) -> list[dict[str, str]]:
    evidence = []
    if entity.get("source_file"):
        evidence.append({"file": str(entity["source_file"]), "symbol": str(entity.get("name") or entity["id"])})
    return evidence


def merge_evidence(items: list[dict[str, Any] | None]) -> list[dict[str, str]]:
    evidence = []
    for item in items:
        if not item:
            continue
        evidence.extend(item.get("evidence", []) or [])
        if item.get("source_file"):
            evidence.append({"file": str(item["source_file"]), "symbol": str(item.get("source_symbol") or item.get("handler") or item.get("id"))})
        if item.get("router_file"):
            evidence.append({"file": str(item["router_file"]), "symbol": str(item.get("handler") or item.get("id"))})
    seen = set()
    result = []
    for item in evidence:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result


def main() -> dict[str, Any]:
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    apply_state_model(snapshot)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("State model normalized:")
    for key, value in snapshot["state_model_metrics"].items():
        if key != "coverage_by_entity":
            print(f"- {key}: {value}")
    return snapshot["state_model_metrics"]


if __name__ == "__main__":
    main()
