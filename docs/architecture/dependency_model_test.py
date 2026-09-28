import unittest
from copy import deepcopy

from dependency_model import apply_dependency_model


def module(module_id):
    return {"id": module_id, "name": module_id, "entities": [], "services": [], "api": [], "frontend_routes": []}


def entity(entity_id, module_id):
    return {"id": entity_id, "module": module_id}


def service(service_id, module_id, reads=None, writes=None, calls=None):
    return {
        "id": service_id,
        "module": module_id,
        "reads_entities": reads or [],
        "writes_entities": writes or [],
        "calls_services": calls or [],
        "source_type": "EXTRACTED",
        "confidence": "high",
    }


def endpoint(api_id, module_id, calls=None, permission="authenticated"):
    return {"id": api_id, "module": module_id, "service_calls": calls or [], "permission": permission}


BASE = {
    "modules": [
        module("module.auth"),
        module("module.audit"),
        module("module.dashboard"),
        module("module.settings"),
        module("module.participants"),
        module("module.memberships"),
        module("module.teachers"),
        module("module.schedule"),
        module("module.finance"),
        module("module.visits"),
        {**module("module.infrastructure"), "isolation_policy": "EXPECTED_ISOLATED"},
    ],
    "entities": [
        entity("entity.operator", "module.auth"),
        entity("entity.audit_log", "module.audit"),
        entity("entity.participant", "module.participants"),
        entity("entity.membership", "module.memberships"),
        entity("entity.teacher", "module.teachers"),
        entity("entity.schedule_event", "module.schedule"),
        entity("entity.visit", "module.visits"),
    ],
    "services": [],
    "api": [],
    "frontend_routes": [],
    "frontend_components": [],
    "business_rules": [],
    "use_cases": [],
    "relationships": [],
    "cross_module_dependencies": [],
}


class DependencyModelTest(unittest.TestCase):
    def test_auth_is_control_supporting_detail(self):
        snapshot = deepcopy(BASE)
        snapshot["services"] = [service("service.auth.check", "module.auth", reads=["entity.participant"])]

        result = apply_dependency_model(snapshot)
        dep = self.dep(result, "module.auth", "module.participants")

        self.assertEqual(dep["classification"], "CONTROL")
        self.assertEqual(dep["importance"], "SUPPORTING")
        self.assertEqual(dep["default_visibility"], "DETAIL")

    def test_audit_is_observability_supporting(self):
        snapshot = deepcopy(BASE)
        snapshot["services"] = [service("service.audit.record", "module.audit", reads=["entity.schedule_event"])]

        result = apply_dependency_model(snapshot)
        dep = self.dep(result, "module.audit", "module.schedule")

        self.assertEqual(dep["classification"], "OBSERVABILITY")
        self.assertEqual(dep["importance"], "SUPPORTING")

    def test_dashboard_is_ui_composition_supporting(self):
        snapshot = deepcopy(BASE)
        snapshot["frontend_routes"] = [{"id": "route.dashboard", "module": "module.dashboard", "api_dependencies": ["api.finance.summary"]}]
        snapshot["api"] = [endpoint("api.finance.summary", "module.finance")]

        result = apply_dependency_model(snapshot)
        dep = self.dep(result, "module.dashboard", "module.finance")

        self.assertEqual(dep["classification"], "UI_COMPOSITION")
        self.assertEqual(dep["importance"], "SUPPORTING")
        self.assertEqual(dep["default_visibility"], "DETAIL")

    def test_participants_depend_on_memberships_as_secondary_detail(self):
        snapshot = deepcopy(BASE)
        snapshot["services"] = [service("service.participant.summary", "module.participants", reads=["entity.membership"])]

        result = apply_dependency_model(snapshot)
        dep = self.dep(result, "module.participants", "module.memberships")

        self.assertEqual(dep["classification"], "DATA")
        self.assertEqual(dep["importance"], "SECONDARY")
        self.assertEqual(dep["default_visibility"], "DETAIL")

    def test_teachers_are_consumed_by_schedule_not_reverse(self):
        snapshot = deepcopy(BASE)
        snapshot["services"] = [service("service.schedule.create", "module.schedule", reads=["entity.teacher"])]

        result = apply_dependency_model(snapshot)

        self.dep(result, "module.schedule", "module.teachers")
        self.assertIsNone(self.find_dep(result, "module.teachers", "module.schedule"))

    def test_primary_domain_cycle_is_reported(self):
        snapshot = deepcopy(BASE)
        snapshot["cross_module_dependencies"] = [
            {"id": "dependency.schedule_membership", "from": "module.schedule", "to": "module.memberships", "type": "writes", "source_type": "DECLARED", "confidence": "high"},
            {"id": "dependency.finance_memberships", "from": "module.memberships", "to": "module.schedule", "type": "writes", "source_type": "DECLARED", "confidence": "high"},
        ]

        result = apply_dependency_model(snapshot)

        self.assertEqual(result["dependency_metrics"]["primary_dependency_count"], 2)
        self.assertEqual(result["dependency_metrics"]["circular_dependency_count"], 1)

    def test_generation_is_deterministic(self):
        snapshot = deepcopy(BASE)
        snapshot["services"] = [
            service("service.finance.summary", "module.finance", reads=["entity.visit", "entity.membership"]),
            service("service.schedule.create", "module.schedule", writes=["entity.membership"], reads=["entity.teacher"]),
        ]

        first = apply_dependency_model(deepcopy(snapshot))["cross_module_dependencies"]
        second = apply_dependency_model(deepcopy(snapshot))["cross_module_dependencies"]

        self.assertEqual(first, second)

    def find_dep(self, snapshot, source, target):
        return next((dep for dep in snapshot["cross_module_dependencies"] if dep["from"] == source and dep["to"] == target), None)

    def dep(self, snapshot, source, target):
        found = self.find_dep(snapshot, source, target)
        self.assertIsNotNone(found)
        return found


if __name__ == "__main__":
    unittest.main()
