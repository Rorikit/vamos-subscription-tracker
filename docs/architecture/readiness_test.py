import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from readiness import evaluate_model_readiness  # noqa: E402


FIXTURES = Path(__file__).with_name("test-fixtures")
SNAPSHOT_PATH = Path(__file__).with_name("architecture_snapshot.json")


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def model(report: dict, model_id: str) -> dict:
    return next(item for item in report["models"] if item["model"] == model_id)


def diagnostics(report: dict, rule_id: str) -> list[dict]:
    return [item for item in report["diagnostics"] if item["rule_id"] == rule_id]


class ModelReadinessTest(unittest.TestCase):
    def test_fully_ready_snapshot_gives_ready(self):
        report = evaluate_model_readiness(load_fixture("fully_ready.json"))
        statuses = {item["model"]: item["status"] for item in report["models"]}
        self.assertEqual(set(statuses), {
            "SYSTEM_MAP",
            "DOMAIN_MODEL",
            "USE_CASE_MODEL",
            "ACTIVITY_MODEL",
            "STATE_MODEL",
            "SEQUENCE_MODEL",
            "DATA_MODEL",
            "COMPONENT_MODEL",
            "DEPLOYMENT_MODEL",
        })
        self.assertTrue(all(status == "READY" for status in statuses.values()), statuses)

    def test_missing_states_detected(self):
        report = evaluate_model_readiness(load_fixture("partial_state.json"))
        self.assertIn(model(report, "STATE_MODEL")["status"], {"PARTIAL", "MISSING"})

    def test_status_field_without_states_detected(self):
        report = evaluate_model_readiness(load_fixture("partial_state.json"))
        self.assertTrue(diagnostics(report, "STATE-001"))

    def test_rule_changes_status_without_transition_detected(self):
        data = load_fixture("fully_ready.json")
        data["business_rules"].append({"id": "rule.order.reopen", "writes": ["entity.order"], "description": "changes status", "result": "status = reopened"})
        report = evaluate_model_readiness(data)
        self.assertTrue(diagnostics(report, "STATE-003"))

    def test_use_case_without_process_detected(self):
        data = load_fixture("fully_ready.json")
        data["business_processes"] = []
        report = evaluate_model_readiness(data)
        self.assertTrue(diagnostics(report, "USECASE-001"))

    def test_use_case_without_interaction_detected(self):
        report = evaluate_model_readiness(load_fixture("missing_sequences.json"))
        self.assertTrue(diagnostics(report, "USECASE-002"))

    def test_persistent_entity_without_data_table_detected(self):
        data = load_fixture("fully_ready.json")
        data["entity_table_mappings"] = []
        report = evaluate_model_readiness(data)
        self.assertTrue(diagnostics(report, "DATA-001"))

    def test_service_without_component_detected(self):
        data = load_fixture("fully_ready.json")
        data["components"][0]["contains_services"] = []
        report = evaluate_model_readiness(data)
        self.assertTrue(diagnostics(report, "COMPONENT-001"))

    def test_component_without_deployment_detected(self):
        data = load_fixture("fully_ready.json")
        data["component_deployments"] = []
        report = evaluate_model_readiness(data)
        self.assertTrue(diagnostics(report, "DEPLOY-001"))

    def test_expected_isolated_module_is_not_suspicious(self):
        data = load_fixture("fully_ready.json")
        data["modules"].append({"id": "module.health"})
        report = evaluate_model_readiness(data)
        isolated = {item["module"]: item["classification"] for item in report["isolated_modules"]}
        self.assertEqual(isolated["module.health"], "expected")

    def test_isolated_module_with_external_refs_is_suspicious(self):
        report = evaluate_model_readiness(load_fixture("suspicious_isolated_module.json"))
        self.assertTrue(diagnostics(report, "MODULE-ISO-001"))

    def test_missing_cross_module_dependency_candidate_detected(self):
        report = evaluate_model_readiness(load_fixture("suspicious_isolated_module.json"))
        self.assertTrue(diagnostics(report, "MODULE-DEP-001"))
        self.assertEqual(report["dependency_candidates"][0]["from"], "module.b")

    def test_direction_mismatch_detected(self):
        data = load_fixture("suspicious_isolated_module.json")
        data["cross_module_dependencies"] = [{"id": "dep.a.b", "from": "module.a", "to": "module.b", "type": "calls"}]
        report = evaluate_model_readiness(data)
        self.assertTrue(diagnostics(report, "MODULE-DEP-002"))

    def test_source_of_truth_conflict_detected(self):
        data = load_fixture("fully_ready.json")
        data["sources_of_truth"] = [{"id": "sot.money", "concept": "money", "source": {"ref": "entity.order"}, "conflicts": ["manual"]}]
        report = evaluate_model_readiness(data)
        self.assertTrue(diagnostics(report, "SOT-001"))

    def test_traceability_coverage_calculated(self):
        report = evaluate_model_readiness(load_fixture("fully_ready.json"))
        chain = report["traceability_coverage"]["use_case.order.close"]
        self.assertTrue(all(chain.values()), chain)

    def test_report_is_deterministic(self):
        data = load_fixture("fully_ready.json")
        self.assertEqual(evaluate_model_readiness(copy.deepcopy(data)), evaluate_model_readiness(copy.deepcopy(data)))

    def test_real_snapshot_generates_all_models(self):
        data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        report = evaluate_model_readiness(data)
        self.assertEqual(len(report["models"]), 9)
        self.assertTrue(all(item["status"] in {"READY", "PARTIAL", "MISSING", "INVALID"} for item in report["models"]))
        known_ids = {node["id"] for section in [
            "modules",
            "entities",
            "services",
            "api",
            "frontend_routes",
            "frontend_components",
            "roles",
            "permissions",
            "business_rules",
            "use_cases",
            "business_processes",
            "interactions",
            "states",
            "transitions",
            "data_tables",
            "components",
            "deployment_nodes",
            "model_readiness",
        ] for node in data.get(section, []) or []}
        for warning in report["diagnostics"]:
            for item_id in warning["affected_ids"]:
                self.assertTrue(item_id in known_ids or item_id.startswith("sot."), item_id)


if __name__ == "__main__":
    unittest.main()
