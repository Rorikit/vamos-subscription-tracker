import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from architecture_contract import RELATION_TYPES  # noqa: E402
from validate_snapshot import validate  # noqa: E402


def node(item_id: str, **extra):
    return {"id": item_id, "name_ru": item_id, "source_type": "DECLARED", "confidence": "high", "evidence": [{"type": "test", "ref": "fixture"}], **extra}


def fixture():
    return {
        "schema_version": 2,
        "model_contract_version": 1,
        "metadata": {},
        "relation_type_registry": [{"type": item} for item in RELATION_TYPES],
        "modules": [node("module.schedule", entities=["entity.visit"], services=["service.schedule"], api=["api.schedule.create"], frontend_routes=["route.schedule"])],
        "actors": [node("actor.admin", represented_by_role="role.admin")],
        "entities": [
            node("entity.visit", module="module.schedule", table="visits", relationships=["relationship.visit.teacher"], fields=[{"name": "is_cancelled", "type": "Boolean"}]),
            node("entity.teacher", module="module.schedule", table="teachers", relationships=[], fields=[{"name": "is_active", "type": "Boolean"}]),
        ],
        "states": [
            node("state.visit.active", entity="entity.visit", state_kind="DERIVED_STATE", representation={"field": "is_cancelled", "condition": "false"}),
            node("state.visit.cancelled", entity="entity.visit", state_kind="DERIVED_STATE", representation={"field": "is_cancelled", "condition": "true"}),
            node("state.teacher.active", entity="entity.teacher", state_kind="DERIVED_STATE", representation={"field": "is_active", "condition": "true"}),
        ],
        "transitions": [
            node("transition.visit.cancel", entity="entity.visit", from_="ignored", transition_kind="COMPENSATING", trigger_type="API_ACTION", caused_by=["rule.visit.cancel", "service.schedule"], api=["api.schedule.create"], **{"from": "state.visit.active", "to": "state.visit.cancelled", "business_rule": "rule.visit.cancel", "service": "service.schedule"})
        ],
        "relationships": [node("relationship.visit.teacher", type="belongs_to", from_="ignored", **{"from": "entity.visit", "to": "entity.teacher", "owner": "entity.visit"})],
        "services": [node("service.schedule", module="module.schedule", reads_entities=["entity.visit"], writes_entities=["entity.visit"], calls_services=[], called_by=[])],
        "repositories": [],
        "api": [node("api.schedule.create", module="module.schedule", permission="permission.schedule.manage", service_calls=["service.schedule"], reads_entities=[], writes_entities=["entity.visit"])],
        "data_tables": [node("table.visits", entity="entity.visit", columns=[])],
        "components": [node("component.backend", contains_services=["service.schedule"], contains_routes=[], requires_api=[], exposes_api=["api.schedule.create"], contains_tables=[])],
        "deployment_nodes": [node("deployment.backend_container", kind="container")],
        "frontend_routes": [node("route.schedule", module="module.schedule", required_permission="permission.schedule.manage", api_dependencies=["api.schedule.create"])],
        "frontend_components": [],
        "roles": [node("role.admin", permissions=["permission.schedule.manage"])],
        "permissions": [node("permission.schedule.manage", roles=["role.admin"], api=["api.schedule.create"], routes=["route.schedule"])],
        "business_rules": [node("rule.visit.cancel", modules=["module.schedule"], entities=["entity.visit"])],
        "business_processes": [node("process.schedule.cancel", use_case="use_case.schedule.cancel", steps=[{"order": 1, "action": "cancel", "ref": "service.schedule"}])],
        "interactions": [node("interaction.schedule.cancel", use_case="use_case.schedule.cancel", process="process.schedule.cancel", participants=["component.backend", "service.schedule"], messages=[{"order": 1, "from": "component.backend", "to": "service.schedule", "action": "cancel"}])],
        "use_cases": [node("use_case.schedule.cancel", actors=["actor.admin"], required_permissions=["permission.schedule.manage"], entry_points=["route.schedule"], api=["api.schedule.create"], services=["service.schedule"], reads_entities=["entity.visit"], writes_entities=["entity.visit"])],
        "data_flows": [node("flow.schedule.cancel", modules=["module.schedule"], entities=["entity.visit"], services=["service.schedule"], steps=[{"order": 1, "action": "cancel", "ref": "service.schedule"}])],
        "sources_of_truth": [node("sot.visit", concept="visit_status", source={"type": "architecture_ref", "ref": "entity.visit"}, consumers=["service.schedule"])],
        "cross_module_dependencies": [],
        "entity_table_mappings": [node("mapping.entity.visit.table.visits", type="persisted_as", from_="ignored", **{"from": "entity.visit", "to": "table.visits"})],
        "component_deployments": [node("deployment.component.backend", type="deployed_on", from_="ignored", **{"from": "component.backend", "to": "deployment.backend_container"})],
        "traceability": [node("trace.schedule.cancel", use_case="use_case.schedule.cancel", process="process.schedule.cancel", interaction="interaction.schedule.cancel", entities=["entity.visit"], services=["service.schedule"], api=["api.schedule.create"], permissions=["permission.schedule.manage"], tables=["table.visits"])],
        "impact_edges": [],
        "finance": {},
        "schedule": {},
        "notifications": [],
        "technical_debt": [],
        "open_questions": [],
        "model_readiness": [node("readiness.sequence", status="partial", covered_by=["interactions"], gaps=["manual review"])],
    }


class SnapshotValidatorTest(unittest.TestCase):
    def assert_error_contains(self, snapshot, needle):
        report = validate(snapshot)
        self.assertFalse(report["valid"])
        self.assertTrue(any(needle in error for error in report["errors"]), report["errors"])

    def test_valid_fixture_passes(self):
        self.assertTrue(validate(fixture())["valid"])

    def test_duplicate_id_rejected(self):
        data = fixture()
        data["entities"].append(copy.deepcopy(data["entities"][0]))
        self.assert_error_contains(data, "duplicate id")

    def test_unknown_relation_rejected(self):
        data = fixture()
        data["relationships"][0]["type"] = "mystery"
        self.assert_error_contains(data, "invalid relation type")

    def test_dangling_entity_ref_rejected(self):
        data = fixture()
        data["services"][0]["reads_entities"] = ["entity.missing"]
        self.assert_error_contains(data, "missing ref entity.missing")

    def test_invalid_state_owner_rejected(self):
        data = fixture()
        data["states"][0]["entity"] = "entity.missing"
        self.assert_error_contains(data, "state.visit.active.entity")

    def test_cross_entity_transition_rejected(self):
        data = fixture()
        data["transitions"][0]["to"] = "state.teacher.active"
        self.assert_error_contains(data, "transition crosses entity state machines")

    def test_unknown_actor_rejected(self):
        data = fixture()
        data["use_cases"][0]["actors"] = ["actor.missing"]
        self.assert_error_contains(data, "missing ref actor.missing")

    def test_unknown_permission_rejected(self):
        data = fixture()
        data["use_cases"][0]["required_permissions"] = ["permission.missing"]
        self.assert_error_contains(data, "missing ref permission.missing")

    def test_unknown_interaction_participant_rejected(self):
        data = fixture()
        data["interactions"][0]["participants"] = ["service.missing"]
        self.assert_error_contains(data, "missing ref service.missing")

    def test_entity_table_mapping_validated(self):
        data = fixture()
        data["entity_table_mappings"][0]["to"] = "table.missing"
        self.assert_error_contains(data, "missing ref table.missing")

    def test_deployment_ref_validated(self):
        data = fixture()
        data["component_deployments"][0]["to"] = "deployment.missing"
        self.assert_error_contains(data, "missing ref deployment.missing")

    def test_source_of_truth_conflict_warns(self):
        data = fixture()
        data["sources_of_truth"].append(node("sot.visit.duplicate", concept="visit_status", source={"type": "architecture_ref", "ref": "entity.visit"}, consumers=[], conflicts=["test conflict"]))
        report = validate(data)
        self.assertTrue(report["valid"])
        self.assertTrue(any("source-of-truth conflict declared" in warning for warning in report["warnings"]))

    def test_traceability_ref_validated(self):
        data = fixture()
        data["traceability"][0]["api"] = ["api.missing"]
        self.assert_error_contains(data, "missing ref api.missing")


if __name__ == "__main__":
    unittest.main()
