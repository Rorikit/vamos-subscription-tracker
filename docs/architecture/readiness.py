from __future__ import annotations

import json
from collections import defaultdict, deque
from copy import deepcopy
from pathlib import Path
from typing import Any

from architecture_contract import RELATION_TYPES


SNAPSHOT_PATH = Path(__file__).with_name("architecture_snapshot.json")
READY_THRESHOLD = 0.8
PARTIAL_THRESHOLD = 0.01
STATUSES = {"READY", "PARTIAL", "MISSING", "INVALID"}
SEVERITIES = {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}


MODEL_DEFINITIONS = [
    {"id": "SYSTEM_MAP", "name_ru": "Карта системы", "contract": "SYSTEM_MAP.md", "required": ["modules", "cross_module_dependencies"], "optional": []},
    {"id": "DOMAIN_MODEL", "name_ru": "Предметная модель", "contract": "DOMAIN_MODEL.md", "required": ["entities", "relationships"], "optional": ["business_rules"]},
    {"id": "USE_CASE_MODEL", "name_ru": "Use Case", "contract": "USE_CASE_MODEL.md", "required": ["actors", "use_cases"], "optional": ["permissions", "business_processes"]},
    {"id": "ACTIVITY_MODEL", "name_ru": "Бизнес-процессы", "contract": "ACTIVITY_MODEL.md", "required": ["business_processes"], "optional": ["use_cases", "business_rules"]},
    {"id": "STATE_MODEL", "name_ru": "Жизненные циклы", "contract": "STATE_MODEL.md", "required": ["states", "transitions"], "optional": ["business_rules"]},
    {"id": "SEQUENCE_MODEL", "name_ru": "Взаимодействия", "contract": "SEQUENCE_MODEL.md", "required": ["interactions"], "optional": ["business_processes"]},
    {"id": "DATA_MODEL", "name_ru": "Модель данных", "contract": "DATA_MODEL.md", "required": ["data_tables", "entity_table_mappings"], "optional": ["entities"]},
    {"id": "COMPONENT_MODEL", "name_ru": "Компоненты", "contract": "COMPONENT_MODEL.md", "required": ["components"], "optional": ["services", "api"]},
    {"id": "DEPLOYMENT_MODEL", "name_ru": "Развертывание", "contract": "DEPLOYMENT_MODEL.md", "required": ["deployment_nodes", "component_deployments"], "optional": ["components"]},
]


def evaluate_model_readiness(snapshot: dict[str, Any]) -> dict[str, Any]:
    context = build_context(snapshot)
    diagnostics: list[dict[str, Any]] = []
    isolated_modules = analyze_isolated_modules(snapshot, context, diagnostics)
    dependency_candidates = analyze_dependency_candidates(snapshot, context, diagnostics)
    candidates_by_module = defaultdict(list)
    for candidate in dependency_candidates:
        candidates_by_module[candidate["from"]].append(candidate)
    for item in isolated_modules:
        item["candidate_dependencies"] = sorted(candidates_by_module.get(item["module"], []), key=lambda candidate: (candidate["from"], candidate["to"], candidate["type"]))
    traceability_coverage = analyze_traceability(snapshot, context, diagnostics)
    analyze_sources_of_truth(snapshot, diagnostics)

    models = [
        system_map_readiness(snapshot, context, diagnostics, isolated_modules),
        domain_model_readiness(snapshot, context, diagnostics),
        use_case_model_readiness(snapshot, context, diagnostics, traceability_coverage),
        activity_model_readiness(snapshot, context, diagnostics),
        state_model_readiness(snapshot, context, diagnostics),
        sequence_model_readiness(snapshot, context, diagnostics),
        data_model_readiness(snapshot, context, diagnostics),
        component_model_readiness(snapshot, context, diagnostics),
        deployment_model_readiness(snapshot, context, diagnostics),
    ]
    analyze_model_statuses(models, diagnostics)

    report = {
        "schema_version": 1,
        "status_enum": sorted(STATUSES),
        "severity_enum": sorted(SEVERITIES),
        "thresholds": {"ready_default": READY_THRESHOLD, "partial_minimum": PARTIAL_THRESHOLD},
        "models": sorted(models, key=lambda item: item["id"]),
        "diagnostics": sorted(diagnostics, key=diagnostic_sort_key),
        "architecture_coverage": build_architecture_coverage(snapshot, models, diagnostics, isolated_modules, dependency_candidates),
        "traceability_coverage": traceability_coverage,
        "isolated_modules": isolated_modules,
        "dependency_candidates": dependency_candidates,
    }
    return report


def build_context(snapshot: dict[str, Any]) -> dict[str, Any]:
    ids: dict[str, dict[str, Any]] = {}
    owner_by_id: dict[str, str] = {}
    for section in [
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
    ]:
        for item in snapshot.get(section, []) or []:
            ids[item["id"]] = item
            module_id = item.get("module")
            if module_id:
                owner_by_id[item["id"]] = module_id
    for module in snapshot.get("modules", []) or []:
        for key in ["entities", "services", "api", "frontend_routes"]:
            for item_id in module.get(key, []) or []:
                owner_by_id[item_id] = module["id"]
    validation = snapshot.get("validation_report") or {}
    return {
        "ids": ids,
        "owner_by_id": owner_by_id,
        "semantic_errors": validation.get("errors") or [],
        "relation_types": {item.get("type") for item in snapshot.get("relation_type_registry", [])} or set(RELATION_TYPES),
    }


def model_result(
    model_id: str,
    status: str,
    coverage: float,
    summary: str,
    reasons: list[str],
    metrics: dict[str, Any],
    warnings: list[str],
    affected_ids: list[str],
) -> dict[str, Any]:
    return {
        "id": f"readiness.{model_id.lower()}",
        "model": model_id,
        "name_ru": next(item["name_ru"] for item in MODEL_DEFINITIONS if item["id"] == model_id),
        "contract": next(item["contract"] for item in MODEL_DEFINITIONS if item["id"] == model_id),
        "status": status,
        "coverage": round(max(0.0, min(1.0, coverage)), 4),
        "coverage_percent": round(max(0.0, min(1.0, coverage)) * 100),
        "summary": summary,
        "reasons": sorted(set(reasons)),
        "metrics": dict(sorted(metrics.items())),
        "warnings": sorted(set(warnings)),
        "affected_ids": sorted(set(affected_ids)),
    }


def status_from_coverage(coverage: float, has_required_data: bool = True, invalid: bool = False) -> str:
    if invalid:
        return "INVALID"
    if not has_required_data:
        return "MISSING"
    if coverage >= READY_THRESHOLD:
        return "READY"
    if coverage > PARTIAL_THRESHOLD:
        return "PARTIAL"
    return "MISSING"


def add_diagnostic(
    diagnostics: list[dict[str, Any]],
    rule_id: str,
    severity: str,
    message: str,
    model: str | None = None,
    module: str | None = None,
    affected_ids: list[str] | None = None,
    confidence: str = "high",
) -> None:
    diagnostics.append(
        {
            "id": f"diagnostic.{rule_id.lower()}.{len(diagnostics) + 1:04d}",
            "rule_id": rule_id,
            "severity": severity,
            "model": model,
            "module": module,
            "message": message,
            "affected_ids": sorted(set(affected_ids or [])),
            "confidence": confidence,
        }
    )


def diagnostic_sort_key(item: dict[str, Any]) -> tuple[int, str, str]:
    severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    return (severity_rank.get(item["severity"], 99), item["rule_id"], item["id"])


def analyze_model_statuses(models: list[dict[str, Any]], diagnostics: list[dict[str, Any]]) -> None:
    for model in models:
        if model["status"] == "MISSING":
            add_diagnostic(
                diagnostics,
                "READINESS-001",
                "HIGH",
                f"{model['model']} is missing required data for its contract.",
                model["model"],
                affected_ids=model.get("affected_ids", []),
            )
        elif model["status"] == "PARTIAL":
            add_diagnostic(
                diagnostics,
                "READINESS-002",
                "MEDIUM",
                f"{model['model']} coverage is below READY threshold: {model['coverage_percent']}%.",
                model["model"],
                affected_ids=model.get("affected_ids", []),
            )


def system_map_readiness(snapshot: dict[str, Any], context: dict[str, Any], diagnostics: list[dict[str, Any]], isolated: list[dict[str, Any]]) -> dict[str, Any]:
    modules = snapshot.get("modules", []) or []
    deps = snapshot.get("cross_module_dependencies", []) or []
    invalid = bool(context["semantic_errors"])
    module_ids = {item["id"] for item in modules}
    degree = defaultdict(int)
    graph = defaultdict(set)
    for dep in deps:
        graph[dep["from"]].add(dep["to"])
        graph[dep["to"]].add(dep["from"])
        degree[dep["from"]] += 1
        degree[dep["to"]] += 1
    components = connected_components(module_ids, graph)
    connected = {module_id for module_id in module_ids if degree[module_id] > 0}
    suspicious = [item for item in isolated if item["classification"] == "suspicious"]
    coverage = len(connected) / len(modules) if modules else 0
    if suspicious:
        coverage = min(coverage, 0.79)
    status = status_from_coverage(coverage, bool(modules), invalid)
    reasons = []
    if not deps:
        reasons.append("Cross-module dependencies are absent.")
    if suspicious:
        reasons.append(f"{len(suspicious)} isolated modules have external references.")
    warnings = [item["module"] for item in suspicious]
    return model_result(
        "SYSTEM_MAP",
        status,
        coverage,
        f"{len(connected)} of {len(modules)} modules are connected by dependency edges.",
        reasons,
        {
            "module_count": len(modules),
            "dependency_count": len(deps),
            "connected_module_count": len(connected),
            "isolated_module_count": len(modules) - len(connected),
            "connected_components_count": len(components),
            "largest_component_size": max((len(item) for item in components), default=0),
            "dependency_coverage_ratio": round(coverage, 4),
        },
        warnings,
        [item["module"] for item in isolated],
    )


def domain_model_readiness(snapshot: dict[str, Any], context: dict[str, Any], diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    entities = snapshot.get("entities", []) or []
    relationships = snapshot.get("relationships", []) or []
    related = {rel.get("from") for rel in relationships} | {rel.get("to") for rel in relationships}
    business_rule_entities = {entity for rule in snapshot.get("business_rules", []) or [] for entity in (rule.get("entities") or rule.get("reads") or [])}
    isolated = sorted(entity["id"] for entity in entities if entity["id"] not in related)
    semantic = [rel for rel in relationships if rel.get("source_type") != "EXTRACTED" or rel.get("type") not in {"belongs_to", "one_to_many", "many_to_one"}]
    coverage = len(related & {entity["id"] for entity in entities}) / len(entities) if entities else 0
    if not semantic and relationships:
        coverage = min(coverage, 0.79)
    for entity_id in isolated:
        add_diagnostic(diagnostics, "COVERAGE-001", "LOW", f"{entity_id} has no domain relationship.", "DOMAIN_MODEL", affected_ids=[entity_id])
    return model_result(
        "DOMAIN_MODEL",
        status_from_coverage(coverage, bool(entities and relationships), bool(context["semantic_errors"])),
        coverage,
        f"{len(related & {entity['id'] for entity in entities})} of {len(entities)} entities participate in relationships.",
        ["Relationships look persistence-oriented; semantic domain coverage should be reviewed."] if not semantic and relationships else [],
        {
            "entity_count": len(entities),
            "relationship_count": len(relationships),
            "isolated_entity_count": len(isolated),
            "entities_with_business_rules": len(business_rule_entities),
            "entities_without_relationships": len(isolated),
            "semantic_relationship_ratio": round(len(semantic) / len(relationships), 4) if relationships else 0,
        },
        isolated,
        isolated,
    )


def use_case_model_readiness(snapshot: dict[str, Any], context: dict[str, Any], diagnostics: list[dict[str, Any]], traceability: dict[str, Any]) -> dict[str, Any]:
    use_cases = snapshot.get("use_cases", []) or []
    actors = snapshot.get("actors", []) or []
    processes_by_uc = {process.get("use_case") for process in snapshot.get("business_processes", []) or [] if process.get("use_case")}
    with_process = [uc["id"] for uc in use_cases if uc["id"] in processes_by_uc]
    with_permissions = [uc["id"] for uc in use_cases if uc.get("required_permissions")]
    for uc in use_cases:
        if uc["id"] not in processes_by_uc:
            add_diagnostic(diagnostics, "USECASE-001", "MEDIUM", f"{uc['id']} has no BusinessProcess.", "USE_CASE_MODEL", affected_ids=[uc["id"]])
    coverage = average_ratio([
        len(with_process) / len(use_cases) if use_cases else 0,
        len(with_permissions) / len(use_cases) if use_cases else 0,
        len(actors) / max(1, len(snapshot.get("roles", []) or [])),
    ])
    return model_result(
        "USE_CASE_MODEL",
        status_from_coverage(coverage, bool(use_cases and actors), bool(context["semantic_errors"])),
        coverage,
        f"{len(with_process)} of {len(use_cases)} use cases are linked to business processes.",
        [],
        {
            "use_case_count": len(use_cases),
            "actor_count": len(actors),
            "use_cases_with_process": len(with_process),
            "use_cases_without_process": len(use_cases) - len(with_process),
            "use_cases_with_permissions": len(with_permissions),
            "declared_use_case_count": sum(1 for uc in use_cases if uc.get("source_type") == "DECLARED"),
            "extracted_use_case_count": sum(1 for uc in use_cases if uc.get("source_type") == "EXTRACTED"),
            "medium_low_confidence_count": sum(1 for uc in use_cases if uc.get("confidence") in {"medium", "low"}),
        },
        [uc_id for uc_id, chain in traceability.items() if not chain.get("process")],
        [uc["id"] for uc in use_cases],
    )


def activity_model_readiness(snapshot: dict[str, Any], context: dict[str, Any], diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    processes = snapshot.get("business_processes", []) or []
    use_cases = snapshot.get("use_cases", []) or []
    with_uc = [process["id"] for process in processes if process.get("use_case")]
    with_rules = [process["id"] for process in processes if any(str((step or {}).get("ref", "")).startswith("rule.") for step in process.get("steps", []) or [])]
    with_decisions = [process["id"] for process in processes if any((step or {}).get("type") in {"decision", "guard"} for step in process.get("steps", []) or [])]
    process_uc = {process.get("use_case") for process in processes if process.get("use_case")}
    without_process = [uc["id"] for uc in use_cases if uc["id"] not in process_uc]
    for uc_id in without_process:
        add_diagnostic(diagnostics, "USECASE-001", "MEDIUM", f"{uc_id} has no process for Activity Model.", "ACTIVITY_MODEL", affected_ids=[uc_id])
    coverage = len(with_uc) / len(processes) if processes else 0
    if not with_decisions and processes:
        coverage = min(coverage, 0.79)
    return model_result(
        "ACTIVITY_MODEL",
        status_from_coverage(coverage, bool(processes), bool(context["semantic_errors"])),
        coverage,
        f"{len(with_uc)} of {len(processes)} processes are linked to use cases.",
        ["Processes are mostly linear; decisions and guards are not fully modeled."] if processes and not with_decisions else [],
        {
            "business_process_count": len(processes),
            "processes_with_use_case": len(with_uc),
            "processes_without_use_case": len(processes) - len(with_uc),
            "use_cases_without_process": len(without_process),
            "processes_with_decisions": len(with_decisions),
            "processes_with_rules": len(with_rules),
        },
        without_process,
        [process["id"] for process in processes],
    )


def state_model_readiness(snapshot: dict[str, Any], context: dict[str, Any], diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    entities = snapshot.get("entities", []) or []
    states = snapshot.get("states", []) or []
    transitions = snapshot.get("transitions", []) or []
    stateful_metadata = snapshot.get("stateful_entities", []) or []
    if stateful_metadata:
        stateful = [item["entity"] for item in stateful_metadata if item.get("status") != "NOT_STATEFUL"]
        not_stateful = [item["entity"] for item in stateful_metadata if item.get("status") == "NOT_STATEFUL"]
    else:
        stateful = [entity["id"] for entity in entities if is_stateful(entity, snapshot)]
        not_stateful = []
    entities_with_states = {state.get("entity") for state in states}
    entities_with_transitions = {transition.get("entity") for transition in transitions}
    modeled = sorted(set(stateful) & entities_with_states & entities_with_transitions)
    without_states = sorted(set(stateful) - entities_with_states)
    without_transitions = sorted((set(stateful) & entities_with_states) - entities_with_transitions)
    rules_with_transitions = {ref for transition in transitions for ref in transition_refs(transition) if str(ref).startswith("rule.")}
    apis_with_transitions = {ref for transition in transitions for ref in (transition.get("api") or [])}
    lifecycle_api_ids = lifecycle_api_actions(snapshot)
    uncovered_lifecycle_apis = sorted(set(lifecycle_api_ids) - apis_with_transitions)
    for entity_id in without_states:
        add_diagnostic(diagnostics, "STATE-001", "HIGH", f"{entity_id} has status/state signs but no canonical states.", "STATE_MODEL", affected_ids=[entity_id])
    for entity_id in without_transitions:
        add_diagnostic(diagnostics, "STATE-002", "HIGH", f"{entity_id} has states but no transitions.", "STATE_MODEL", affected_ids=[entity_id])
    for rule in snapshot.get("business_rules", []) or []:
        written = set(rule.get("writes") or rule.get("writes_entities") or [])
        if written & set(stateful) and rule_changes_lifecycle(rule) and rule["id"] not in rules_with_transitions:
            add_diagnostic(diagnostics, "STATE-003", "HIGH", f"{rule['id']} changes stateful data without canonical transition.", "STATE_MODEL", affected_ids=[rule["id"], *sorted(written & set(stateful))])
    for api_id in uncovered_lifecycle_apis:
        add_diagnostic(diagnostics, "STATE-004", "MEDIUM", f"{api_id} mutates lifecycle data but has no canonical transition mapping.", "STATE_MODEL", affected_ids=[api_id], confidence="medium")
    coverage = len(modeled) / len(stateful) if stateful else 1
    if uncovered_lifecycle_apis:
        coverage = min(coverage, 0.79)
    return model_result(
        "STATE_MODEL",
        status_from_coverage(coverage, bool(states and stateful), bool(context["semantic_errors"])),
        coverage,
        f"{len(modeled)} of {len(stateful)} potential stateful entities have states and transitions.",
        [f"{entity_id} is stateful but incomplete." for entity_id in sorted(set(without_states + without_transitions))],
        {
            "potential_stateful_entities": len(stateful),
            "not_stateful_entities": len(not_stateful),
            "modeled_stateful_entities": len(modeled),
            "unmodeled_stateful_entities": len(set(without_states + without_transitions)),
            "state_count": len(states),
            "transition_count": len(transitions),
            "persisted_state_count": sum(1 for state in states if state.get("state_kind") == "PERSISTED_STATE"),
            "derived_state_count": sum(1 for state in states if state.get("state_kind") == "DERIVED_STATE"),
            "derived_state_group_count": len(snapshot.get("derived_state_groups", []) or []),
            "compensating_transition_count": sum(1 for item in transitions if item.get("transition_kind") == "COMPENSATING"),
            "lazy_time_transition_count": sum(1 for item in transitions if item.get("execution") == "lazy evaluation"),
            "uncovered_lifecycle_api_count": len(uncovered_lifecycle_apis),
        },
        without_states + without_transitions + uncovered_lifecycle_apis,
        stateful + not_stateful,
    )


def transition_refs(transition: dict[str, Any]) -> list[str]:
    refs = []
    if transition.get("business_rule"):
        refs.append(transition["business_rule"])
    refs.extend(transition.get("caused_by") or [])
    return refs


def lifecycle_api_actions(snapshot: dict[str, Any]) -> list[str]:
    lifecycle_verbs = ["freeze", "unfreeze", "cancel", "complete", "return", "pay", "unpay"]
    lifecycle_entities = {
        item.get("entity")
        for item in snapshot.get("stateful_entities", []) or []
        if item.get("status") != "NOT_STATEFUL"
    }
    result = []
    for api in snapshot.get("api", []) or []:
        writes = set(api.get("writes_entities") or [])
        action = str(api["id"]).split(".")[-1]
        path_tail = str(api.get("path") or "").rstrip("/").split("/")[-1]
        if writes & lifecycle_entities and (action in lifecycle_verbs or path_tail in lifecycle_verbs):
            result.append(api["id"])
    return result


def rule_changes_lifecycle(rule: dict[str, Any]) -> bool:
    haystack = " ".join(str(rule.get(key) or "") for key in ["id", "title", "description", "condition", "result", "source_symbol"]).lower()
    lifecycle_markers = ["status =", "is_cancelled", "attendance_status", "paid =", "remaining_lessons == 0", "end_date < today"]
    creation_only_markers = ["creates four weekly events", "create_practice_rental", "payment obligation dto", "ensures monthly rows"]
    if any(marker in haystack for marker in creation_only_markers):
        return False
    return any(marker in haystack for marker in lifecycle_markers)


def sequence_model_readiness(snapshot: dict[str, Any], context: dict[str, Any], diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    interactions = snapshot.get("interactions", []) or []
    use_cases = snapshot.get("use_cases", []) or []
    with_uc = [item["id"] for item in interactions if item.get("use_case")]
    with_process = [item["id"] for item in interactions if item.get("process")]
    interaction_uc = {item.get("use_case") for item in interactions if item.get("use_case")}
    without_interaction = [uc["id"] for uc in use_cases if uc["id"] not in interaction_uc]
    unordered = [item["id"] for item in interactions if not is_ordered([message.get("order") for message in item.get("messages", []) or []])]
    for uc_id in without_interaction:
        add_diagnostic(diagnostics, "USECASE-002", "MEDIUM", f"{uc_id} has no explicit Interaction.", "SEQUENCE_MODEL", affected_ids=[uc_id])
    coverage = len(interaction_uc) / len(use_cases) if use_cases else 0
    if interactions and any(item.get("source_type") == "DERIVED" for item in interactions):
        coverage = min(coverage, 0.79)
    return model_result(
        "SEQUENCE_MODEL",
        status_from_coverage(coverage, bool(interactions), bool(context["semantic_errors"] or unordered)),
        coverage,
        f"{len(interaction_uc)} of {len(use_cases)} use cases have interactions.",
        ["Interactions are derived, so sequence model is a candidate rather than fully canonical."] if interactions else [],
        {
            "interaction_count": len(interactions),
            "interactions_with_use_case": len(with_uc),
            "interactions_with_process": len(with_process),
            "use_cases_with_interaction": len(interaction_uc),
            "use_cases_without_interaction": len(without_interaction),
            "invalid_participant_refs": 0,
            "unordered_interactions": len(unordered),
        },
        without_interaction + unordered,
        [item["id"] for item in interactions],
    )


def data_model_readiness(snapshot: dict[str, Any], context: dict[str, Any], diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    entities = snapshot.get("entities", []) or []
    persistent = [entity["id"] for entity in entities if entity.get("table")]
    mappings = snapshot.get("entity_table_mappings", []) or []
    mapped = {mapping.get("from") for mapping in mappings}
    unmapped = sorted(set(persistent) - mapped)
    for entity_id in unmapped:
        add_diagnostic(diagnostics, "DATA-001", "HIGH", f"{entity_id} has table field but no DataTable mapping.", "DATA_MODEL", affected_ids=[entity_id])
    tables = snapshot.get("data_tables", []) or []
    fk_count = sum(len(table.get("foreign_keys") or []) for table in tables)
    constraint_count = sum(len(table.get("constraints") or []) for table in tables)
    index_count = sum(len(table.get("indexes") or []) for table in tables)
    coverage = len(mapped & set(persistent)) / len(persistent) if persistent else 1
    if not any(table.get("constraints") for table in tables):
        coverage = min(coverage, 0.79)
    return model_result(
        "DATA_MODEL",
        status_from_coverage(coverage, bool(tables and mappings), bool(context["semantic_errors"])),
        coverage,
        f"{len(mapped & set(persistent))} of {len(persistent)} persistent entities are mapped to DataTable.",
        ["Constraints are sparse or inferred; physical model needs owner review."] if tables and constraint_count == 0 else [],
        {
            "persistent_entity_count": len(persistent),
            "data_table_count": len(tables),
            "mapped_entity_count": len(mapped & set(persistent)),
            "unmapped_entity_count": len(unmapped),
            "fk_count": fk_count,
            "constraint_count": constraint_count,
            "index_count": index_count,
        },
        unmapped,
        persistent,
    )


def component_model_readiness(snapshot: dict[str, Any], context: dict[str, Any], diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    services = [service["id"] for service in snapshot.get("services", []) or []]
    components = snapshot.get("components", []) or []
    mapped_services = {service_id for component in components for service_id in component.get("contains_services", []) or []}
    unmapped = sorted(set(services) - mapped_services)
    for service_id in unmapped:
        add_diagnostic(diagnostics, "COMPONENT-001", "HIGH", f"{service_id} is not mapped to architecture Component.", "COMPONENT_MODEL", affected_ids=[service_id])
    api = [endpoint["id"] for endpoint in snapshot.get("api", []) or []]
    mapped_api = {api_id for component in components for api_id in component.get("exposes_api", []) or component.get("requires_api", []) or []}
    coverage = average_ratio([
        len(mapped_services) / len(services) if services else 1,
        len(mapped_api) / len(api) if api else 1,
    ])
    return model_result(
        "COMPONENT_MODEL",
        status_from_coverage(coverage, bool(components), bool(context["semantic_errors"])),
        coverage,
        f"{len(mapped_services)} of {len(services)} services are mapped to architecture components.",
        [],
        {
            "architecture_component_count": len(components),
            "frontend_ui_component_count": len(snapshot.get("frontend_components", []) or []),
            "services_mapped_to_components": len(mapped_services),
            "apis_mapped_to_components": len(mapped_api),
            "unmapped_services": len(unmapped),
        },
        unmapped,
        [component["id"] for component in components],
    )


def deployment_model_readiness(snapshot: dict[str, Any], context: dict[str, Any], diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    components = [component["id"] for component in snapshot.get("components", []) or []]
    deployments = snapshot.get("component_deployments", []) or []
    deployed = {item.get("from") for item in deployments}
    undeployed = sorted(set(components) - deployed)
    for component_id in undeployed:
        add_diagnostic(diagnostics, "DEPLOY-001", "HIGH", f"{component_id} is not mapped to DeploymentNode.", "DEPLOYMENT_MODEL", affected_ids=[component_id])
    coverage = len(deployed & set(components)) / len(components) if components else 0
    if any(node.get("confidence") != "high" for node in snapshot.get("deployment_nodes", []) or []):
        coverage = min(coverage, 0.79)
    return model_result(
        "DEPLOYMENT_MODEL",
        status_from_coverage(coverage, bool(snapshot.get("deployment_nodes") and deployments), bool(context["semantic_errors"])),
        coverage,
        f"{len(deployed & set(components))} of {len(components)} architecture components are deployed.",
        ["Production host topology has declared/medium-confidence parts."] if coverage < 0.8 and deployments else [],
        {
            "deployment_node_count": len(snapshot.get("deployment_nodes", []) or []),
            "deployed_component_count": len(deployed & set(components)),
            "undeployed_component_count": len(undeployed),
        },
        undeployed,
        components,
    )


def analyze_traceability(snapshot: dict[str, Any], context: dict[str, Any], diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    processes_by_uc = defaultdict(list)
    interactions_by_uc = defaultdict(list)
    trace_by_uc = defaultdict(list)
    for process in snapshot.get("business_processes", []) or []:
        if process.get("use_case"):
            processes_by_uc[process["use_case"]].append(process)
    for interaction in snapshot.get("interactions", []) or []:
        if interaction.get("use_case"):
            interactions_by_uc[interaction["use_case"]].append(interaction)
    for trace in snapshot.get("traceability", []) or []:
        if trace.get("use_case"):
            trace_by_uc[trace["use_case"]].append(trace)

    coverage = {}
    for use_case in snapshot.get("use_cases", []) or []:
        use_case_id = use_case["id"]
        traces = trace_by_uc.get(use_case_id, [])
        chain = {
            "actor": bool(use_case.get("actors")),
            "permission": bool(use_case.get("required_permissions")),
            "process": bool(processes_by_uc.get(use_case_id)),
            "interaction": bool(interactions_by_uc.get(use_case_id)),
            "api": bool(use_case.get("api") or any(trace.get("api") for trace in traces)),
            "service": bool(use_case.get("services") or any(trace.get("services") for trace in traces)),
            "entity": bool(use_case.get("reads_entities") or use_case.get("writes_entities") or any(trace.get("entities") for trace in traces)),
            "data": bool(any(trace.get("tables") for trace in traces)),
        }
        coverage[use_case_id] = chain
        if not all(chain.values()):
            missing = [key for key, value in chain.items() if not value]
            add_diagnostic(diagnostics, "TRACE-001", "MEDIUM", f"{use_case_id} traceability chain incomplete: {', '.join(missing)}.", affected_ids=[use_case_id])
    return dict(sorted(coverage.items()))


def analyze_isolated_modules(snapshot: dict[str, Any], context: dict[str, Any], diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deps = snapshot.get("cross_module_dependencies", []) or []
    degree = defaultdict(int)
    for dep in deps:
        degree[dep.get("from")] += 1
        degree[dep.get("to")] += 1
    results = []
    for module in sorted(snapshot.get("modules", []) or [], key=lambda item: item["id"]):
        module_id = module["id"]
        if degree[module_id] > 0:
            continue
        external_refs = observed_external_refs_for_module(snapshot, context, module_id)
        classification = "suspicious" if external_refs else "expected"
        if classification == "suspicious":
            add_diagnostic(
                diagnostics,
                "MODULE-ISO-001",
                "HIGH",
                f"{module_id} is isolated in graph but has external references.",
                "SYSTEM_MAP",
                module_id,
                [module_id, *external_refs],
                confidence="medium",
            )
        results.append(
            {
                "module": module_id,
                "graph_degree": degree[module_id],
                "classification": classification,
                "observed_external_references": external_refs,
                "candidate_dependencies": [],
                "confidence": "medium" if external_refs else "high",
            }
        )
    return results


def analyze_dependency_candidates(snapshot: dict[str, Any], context: dict[str, Any], diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = {(dep.get("from"), dep.get("to")) for dep in snapshot.get("cross_module_dependencies", []) or []}
    observed = {
        (item.get("from"), item.get("to"))
        for item in snapshot.get("observed_interactions", []) or []
        if item.get("from") and item.get("to")
    } or observed_module_pairs(snapshot, context)
    candidates = []
    for pair in sorted(observed):
        if pair not in existing:
            candidate = {
                "from": pair[0],
                "to": pair[1],
                "type": "observed_reference",
                "confidence": "medium",
            }
            candidates.append(candidate)
            add_diagnostic(diagnostics, "MODULE-DEP-001", "MEDIUM", f"Observed cross-module interaction {pair[0]} -> {pair[1]} has no dependency edge.", "SYSTEM_MAP", pair[0], list(pair), confidence="medium")
    for dep_from, dep_to in sorted(existing):
        if (dep_from, dep_to) not in observed and (dep_to, dep_from) in observed:
            add_diagnostic(diagnostics, "MODULE-DEP-002", "MEDIUM", f"Dependency direction may be mismatched: {dep_from} -> {dep_to}.", "SYSTEM_MAP", dep_from, [dep_from, dep_to], confidence="medium")
    for dep in snapshot.get("cross_module_dependencies", []) or []:
        if dep.get("confidence") == "low":
            candidates.append({"from": dep.get("from"), "to": dep.get("to"), "type": "review_required", "confidence": "low"})
            add_diagnostic(
                diagnostics,
                "DEPENDENCY_REVIEW_REQUIRED",
                "MEDIUM",
                f"{dep.get('id')} has low confidence dependency classification.",
                "SYSTEM_MAP",
                dep.get("from"),
                [dep.get("id"), dep.get("from"), dep.get("to")],
                confidence="low",
            )
    return candidates


def analyze_sources_of_truth(snapshot: dict[str, Any], diagnostics: list[dict[str, Any]]) -> None:
    for source in snapshot.get("sources_of_truth", []) or []:
        if source.get("conflicts"):
            add_diagnostic(
                diagnostics,
                "SOT-001",
                "MEDIUM",
                f"{source.get('id')} declares Source of Truth conflict.",
                affected_ids=[source.get("id")],
                confidence=str(source.get("confidence") or "medium"),
            )


def observed_module_pairs(snapshot: dict[str, Any], context: dict[str, Any]) -> set[tuple[str, str]]:
    pairs = set()
    owner = context["owner_by_id"]
    for section in ["services", "api", "frontend_routes", "frontend_components", "business_rules", "use_cases"]:
        for item in snapshot.get(section, []) or []:
            source_module = item.get("module") or owner.get(item["id"])
            if not source_module:
                continue
            refs = refs_from_item(item)
            for ref in refs:
                target_module = owner.get(ref)
                if target_module and target_module != source_module:
                    pairs.add((source_module, target_module))
    for rel in snapshot.get("relationships", []) or []:
        rel_from = owner.get(rel.get("from"))
        rel_to = owner.get(rel.get("to"))
        if rel_from and rel_to and rel_from != rel_to:
            pairs.add((rel_from, rel_to))
    return pairs


def observed_external_refs_for_module(snapshot: dict[str, Any], context: dict[str, Any], module_id: str) -> list[str]:
    owner = context["owner_by_id"]
    refs = set()
    for item_id, item_owner in owner.items():
        if item_owner == module_id:
            continue
        item = context["ids"].get(item_id)
        if not item:
            continue
        for ref in refs_from_item(item):
            if owner.get(ref) == module_id:
                refs.add(item_id)
    return sorted(refs)


def refs_from_item(item: dict[str, Any]) -> list[str]:
    refs = []
    for key in [
        "reads_entities",
        "writes_entities",
        "calls_services",
        "service_calls",
        "api_dependencies",
        "reads",
        "writes",
        "entities",
        "services",
        "api",
        "entry_points",
    ]:
        refs.extend(value for value in item.get(key, []) or [] if isinstance(value, str))
    return refs


def build_architecture_coverage(snapshot: dict[str, Any], models: list[dict[str, Any]], diagnostics: list[dict[str, Any]], isolated: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    by_status = defaultdict(int)
    by_severity = defaultdict(int)
    for model in models:
        by_status[model["status"]] += 1
    for diagnostic in diagnostics:
        by_severity[diagnostic["severity"]] += 1
    dependency_metrics = snapshot.get("dependency_metrics") or {}
    return {
        "schema_validity": snapshot.get("schema_version") == 2,
        "semantic_validity": bool((snapshot.get("validation_report") or {}).get("valid")),
        "model_readiness": dict(sorted(by_status.items())),
        "coverage_warnings": len(diagnostics),
        "warnings_by_severity": dict(sorted(by_severity.items())),
        "suspicious_isolated_modules": [item["module"] for item in isolated if item["classification"] == "suspicious"],
        "source_of_truth_conflicts": [item.get("id") for item in snapshot.get("sources_of_truth", []) or [] if item.get("conflicts")],
        "dependency_candidate_count": len(candidates),
        "observed_interaction_count": dependency_metrics.get("observed_interaction_count", len(snapshot.get("observed_interactions", []) or [])),
        "canonical_dependency_count": dependency_metrics.get("canonical_dependency_count", len(snapshot.get("cross_module_dependencies", []) or [])),
        "primary_dependency_count": dependency_metrics.get("primary_dependency_count", 0),
        "secondary_dependency_count": dependency_metrics.get("secondary_dependency_count", 0),
        "supporting_dependency_count": dependency_metrics.get("supporting_dependency_count", 0),
        "unclassified_candidate_count": dependency_metrics.get("unclassified_candidate_count", 0),
        "suspicious_isolated_count": len([item for item in isolated if item["classification"] == "suspicious"]),
        "circular_dependency_count": len(snapshot.get("architectural_cycles", []) or []),
    }


def connected_components(nodes: set[str], graph: dict[str, set[str]]) -> list[set[str]]:
    seen = set()
    components = []
    for node_id in sorted(nodes):
        if node_id in seen:
            continue
        component = set()
        queue = deque([node_id])
        seen.add(node_id)
        while queue:
            current = queue.popleft()
            component.add(current)
            for next_id in sorted(graph[current]):
                if next_id not in seen:
                    seen.add(next_id)
                    queue.append(next_id)
        components.append(component)
    return components


def is_stateful(entity: dict[str, Any], snapshot: dict[str, Any]) -> bool:
    if entity.get("enum_values"):
        return True
    fields = entity.get("fields", []) or []
    if any(str(field.get("name", "")).lower() in {"status", "state", "attendance_status"} for field in fields):
        return True
    entity_id = entity["id"]
    for rule in snapshot.get("business_rules", []) or []:
        if entity_id in (rule.get("writes") or rule.get("writes_entities") or []):
            if "status" in str(rule.get("description", "")).lower() or "state" in str(rule.get("description", "")).lower():
                return True
    return False


def average_ratio(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0


def is_ordered(values: list[Any]) -> bool:
    normalized = [value for value in values if isinstance(value, int)]
    return normalized == sorted(normalized) and len(normalized) == len(values)


def apply_readiness_report(snapshot: dict[str, Any]) -> dict[str, Any]:
    report = evaluate_model_readiness(snapshot)
    snapshot["readiness_report"] = report
    snapshot["model_readiness"] = [
        {
            "id": model["id"],
            "model": model["model"],
            "name_ru": model["name_ru"],
            "status": model["status"],
            "coverage_percent": model["coverage_percent"],
            "summary": model["summary"],
            "reasons": model["reasons"],
            "metrics": model["metrics"],
            "warnings": model["warnings"],
            "source_type": "DERIVED",
            "confidence": "high",
        }
        for model in report["models"]
    ]
    return snapshot


def main() -> dict[str, Any]:
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    apply_readiness_report(snapshot)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = snapshot["readiness_report"]
    print("Readiness report generated:")
    for model in report["models"]:
        print(f"- {model['model']}: {model['status']} ({model['coverage_percent']}%)")
    return report


if __name__ == "__main__":
    main()
