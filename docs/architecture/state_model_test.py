import unittest
from copy import deepcopy

from readiness import evaluate_model_readiness
from state_model import apply_state_model


def entity(entity_id, fields, enum_values=None):
    return {
        "id": entity_id,
        "name": entity_id,
        "module": "module.test",
        "source_file": f"{entity_id}.py",
        "fields": fields,
        "enum_values": enum_values or [],
    }


def field(name, field_type="String", default=None):
    return {"name": name, "type": field_type, "default": default}


BASE = {
    "schema_version": 2,
    "model_contract_version": 1,
    "modules": [{"id": "module.test"}],
    "entities": [
        entity("entity.membership", [field("status", "Enum"), field("remaining_lessons"), field("end_date")], ["active", "finished", "expired", "frozen", "cancelled"]),
        entity("entity.schedule_event", [field("status"), field("event_type")], {"ScheduleEventStatus": ["scheduled", "completed", "cancelled"]}),
        entity("entity.schedule_event_participant", [field("attendance_status")], {"AttendanceStatus": ["planned", "attended", "absent", "cancelled", "refunded"]}),
        entity("entity.practice_rental", [field("status")], ["active", "cancelled"]),
        entity("entity.extra_expense", [field("status")], ["active", "cancelled"]),
        entity("entity.visit", [field("is_cancelled", "Boolean")]),
        entity("entity.monthly_expense", [field("paid", "Boolean"), field("paid_at"), field("year"), field("month")]),
        entity("entity.operator", [field("role", "Enum"), field("is_active", "Boolean")], ["admin", "operator", "finance"]),
    ],
    "business_rules": [
        {"id": "rule.membership.complete_when_empty", "writes_entities": ["entity.membership"], "evidence": []},
        {"id": "rule.membership.expire_refresh", "writes_entities": ["entity.membership"], "evidence": []},
        {"id": "rule.visit.return_once", "writes_entities": [], "evidence": []},
        {"id": "rule.visit.return_restores_membership", "writes_entities": ["entity.visit", "entity.membership"], "evidence": []},
        {"id": "rule.schedule.complete_creates_visits", "writes_entities": ["entity.schedule_event", "entity.schedule_event_participant", "entity.visit", "entity.membership"], "evidence": []},
        {"id": "rule.schedule.cancel_completed_returns_visits", "writes_entities": ["entity.schedule_event", "entity.visit", "entity.membership"], "evidence": []},
    ],
    "services": [{"id": f"service.{name}", "evidence": []} for name in ["memberships", "schedule_events", "practice", "extra_expenses", "payment_obligations"]],
    "api": [{"id": f"api.{name}", "writes_entities": [], "evidence": []} for name in [
        "schedule.complete",
        "schedule.cancel",
        "schedule.return_participant",
        "schedule.remove_participant",
        "memberships.list",
        "memberships.get",
        "memberships.freeze",
        "memberships.unfreeze",
        "memberships.cancel",
        "practice_rentals.cancel",
        "extra_expenses.cancel",
        "visits.cancel",
        "payment_obligations.pay",
        "payment_obligations.unpay",
    ]],
    "states": [],
    "transitions": [],
}


class StateModelTest(unittest.TestCase):
    def test_persisted_enum_states_detected(self):
        result = apply_state_model(deepcopy(BASE))
        membership_states = [s for s in result["states"] if s["entity"] == "entity.membership"]

        self.assertEqual({s["name"] for s in membership_states}, {"active", "finished", "expired", "frozen", "cancelled"})
        self.assertTrue(all(s["state_kind"] == "PERSISTED_STATE" for s in membership_states))

    def test_boolean_lifecycle_handled(self):
        result = apply_state_model(deepcopy(BASE))
        visit_cancelled = self.state(result, "state.visit.cancelled")

        self.assertEqual(visit_cancelled["state_kind"], "DERIVED_STATE")
        self.assertEqual(visit_cancelled["representation"], {"field": "is_cancelled", "condition": "true"})

    def test_role_is_not_state(self):
        result = apply_state_model(deepcopy(BASE))

        self.assertFalse(any(state["entity"] == "entity.operator" for state in result["states"]))
        self.assertEqual(self.stateful(result, "entity.operator")["status"], "NOT_STATEFUL")

    def test_derived_status_separated_from_persisted_state(self):
        result = apply_state_model(deepcopy(BASE))

        group = next(item for item in result["derived_state_groups"] if item["id"] == "derived_state_group.monthly_expense_obligation_status")
        self.assertEqual(group["state_kind"], "OPERATIONAL_STATUS")
        self.assertEqual({s["name"] for s in result["states"] if s["entity"] == "entity.monthly_expense"}, {"unpaid", "paid"})

    def test_membership_transitions_correct(self):
        result = apply_state_model(deepcopy(BASE))
        ids = {item["id"] for item in result["transitions"] if item["entity"] == "entity.membership"}

        self.assertIn("transition.membership.active_to_finished", ids)
        self.assertIn("transition.membership.active_to_expired", ids)
        self.assertNotIn("transition.membership.cancelled_to_active", ids)

    def test_schedule_transitions_correct(self):
        result = apply_state_model(deepcopy(BASE))
        ids = {item["id"] for item in result["transitions"] if item["entity"] == "entity.schedule_event"}

        self.assertEqual(ids, {
            "transition.schedule_event.scheduled_to_completed",
            "transition.schedule_event.scheduled_to_cancelled",
            "transition.schedule_event.completed_to_cancelled",
        })

    def test_practice_and_extra_expense_cancel_transitions(self):
        result = apply_state_model(deepcopy(BASE))

        self.assertIsNotNone(self.transition(result, "transition.practice_rental.active_to_cancelled"))
        self.assertIsNotNone(self.transition(result, "transition.extra_expense.active_to_cancelled"))

    def test_rule_without_transition_warning(self):
        data = deepcopy(BASE)
        data["business_rules"].append({"id": "rule.membership.fake_status_change", "writes_entities": ["entity.membership"], "result": "status = archived"})
        result = apply_state_model(data)
        report = evaluate_model_readiness(result)

        self.assertTrue(any(item["rule_id"] == "STATE-003" for item in report["diagnostics"]))

    def test_api_mutation_without_lifecycle_mapping_warning(self):
        data = deepcopy(BASE)
        data["api"].append({"id": "api.memberships.cancel_manual_gap", "path": "/memberships/{id}/cancel", "writes_entities": ["entity.membership"]})
        result = apply_state_model(data)
        report = evaluate_model_readiness(result)

        self.assertTrue(any(item["rule_id"] == "STATE-004" for item in report["diagnostics"]))

    def test_time_based_lazy_transition_represented(self):
        result = apply_state_model(deepcopy(BASE))
        transition = self.transition(result, "transition.membership.active_to_expired")

        self.assertEqual(transition["trigger_type"], "TIME_BASED")
        self.assertEqual(transition["execution"], "lazy evaluation")

    def test_compensating_transition_preserved(self):
        result = apply_state_model(deepcopy(BASE))
        transition = self.transition(result, "transition.schedule_event.completed_to_cancelled")

        self.assertEqual(transition["transition_kind"], "COMPENSATING")
        self.assertIn("linked Visit cancelled", transition["side_effects"])

    def test_deterministic_output(self):
        first = apply_state_model(deepcopy(BASE))
        second = apply_state_model(deepcopy(BASE))

        self.assertEqual(first["states"], second["states"])
        self.assertEqual(first["transitions"], second["transitions"])

    def test_readiness_recalculated(self):
        result = apply_state_model(deepcopy(BASE))
        report = evaluate_model_readiness(result)
        state_model = next(item for item in report["models"] if item["model"] == "STATE_MODEL")

        self.assertEqual(state_model["status"], "READY")
        self.assertEqual(state_model["metrics"]["not_stateful_entities"], 1)

    def state(self, snapshot, state_id):
        return next(item for item in snapshot["states"] if item["id"] == state_id)

    def transition(self, snapshot, transition_id):
        return next(item for item in snapshot["transitions"] if item["id"] == transition_id)

    def stateful(self, snapshot, entity_id):
        return next(item for item in snapshot["stateful_entities"] if item["entity"] == entity_id)


if __name__ == "__main__":
    unittest.main()
