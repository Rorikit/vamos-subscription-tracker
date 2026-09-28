import json
from collections import Counter
from pathlib import Path
from typing import Any

from architecture_contract import CONFIDENCE_VALUES, RELATION_TYPES, SOURCE_TYPES


SNAPSHOT_PATH = Path(__file__).with_name("architecture_snapshot.json")

ID_SECTIONS = [
    "modules",
    "actors",
    "entities",
    "stateful_entities",
    "states",
    "transitions",
    "derived_state_groups",
    "relationships",
    "services",
    "repositories",
    "api",
    "data_tables",
    "components",
    "deployment_nodes",
    "frontend_routes",
    "frontend_components",
    "roles",
    "permissions",
    "business_rules",
    "business_processes",
    "interactions",
    "use_cases",
    "data_flows",
    "observed_interactions",
    "cross_module_dependencies",
    "architectural_cycles",
    "entity_table_mappings",
    "component_deployments",
    "technical_debt",
    "notifications",
    "model_readiness",
]

DEPENDENCY_CLASSIFICATIONS = {"DOMAIN", "APPLICATION", "DATA", "CONTROL", "OBSERVABILITY", "UI_COMPOSITION", "INFRASTRUCTURE"}
DEPENDENCY_IMPORTANCE = {"PRIMARY", "SECONDARY", "SUPPORTING"}
DEPENDENCY_VISIBILITY = {"MAIN", "DETAIL", "HIDDEN"}
STATE_KINDS = {"PERSISTED_STATE", "DERIVED_STATE", "OPERATIONAL_STATUS"}
TRANSITION_KINDS = {"NORMAL", "COMPENSATING", "AUTOMATIC", "MANUAL"}
TRIGGER_TYPES = {"API_ACTION", "BUSINESS_RULE", "TIME_BASED", "SYSTEM_ACTION", "USER_ACTION"}


def collect_ids(snapshot: dict[str, Any]) -> dict[str, str]:
    ids: dict[str, str] = {}
    for section in ID_SECTIONS:
        for item in snapshot.get(section, []) or []:
            item_id = item.get("id")
            if item_id:
                ids[item_id] = section
    return ids


def validate(snapshot: dict[str, Any]) -> dict[str, Any]:
    ids = collect_ids(snapshot)
    errors: list[str] = []
    warnings: list[str] = []
    all_ids = [item.get("id") for section in ID_SECTIONS for item in snapshot.get(section, []) or [] if item.get("id")]

    for item_id, count in Counter(all_ids).items():
        if count > 1:
            errors.append(f"duplicate id: {item_id}")

    if snapshot.get("schema_version") != 2:
        errors.append("schema_version must be 2")
    if snapshot.get("model_contract_version") != 1:
        errors.append("model_contract_version must be 1")

    validate_common_metadata(snapshot, ids, errors, warnings)
    validate_modules(snapshot, ids, errors)
    validate_entities(snapshot, ids, errors)
    validate_relationships(snapshot, ids, errors)
    validate_services(snapshot, ids, errors)
    validate_api(snapshot, ids, errors)
    validate_routes_and_components(snapshot, ids, errors)
    validate_rbac(snapshot, ids, errors, warnings)
    validate_use_cases(snapshot, ids, errors, warnings)
    validate_processes(snapshot, ids, errors, warnings)
    validate_states(snapshot, ids, errors)
    validate_interactions(snapshot, ids, errors)
    validate_data_model(snapshot, ids, errors)
    validate_deployments(snapshot, ids, errors)
    validate_sources_of_truth(snapshot, ids, errors, warnings)
    validate_traceability(snapshot, ids, errors)
    validate_dependency_model(snapshot, ids, errors)
    validate_technical_debt(snapshot, ids, errors)

    report = {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "statistics": {
            "modules": len(snapshot.get("modules", [])),
            "entities": len(snapshot.get("entities", [])),
            "stateful_entities": len(snapshot.get("stateful_entities", [])),
            "api": len(snapshot.get("api", [])),
            "actors": len(snapshot.get("actors", [])),
            "states": len(snapshot.get("states", [])),
            "transitions": len(snapshot.get("transitions", [])),
            "data_tables": len(snapshot.get("data_tables", [])),
            "components": len(snapshot.get("components", [])),
            "deployment_nodes": len(snapshot.get("deployment_nodes", [])),
            "traceability": len(snapshot.get("traceability", [])),
        },
    }
    snapshot["validation_report"] = report
    return report


def ensure_ref(errors: list[str], ids: dict[str, str], ref: Any, context: str, allowed_literals: set[Any] | None = None) -> None:
    if ref is None:
        return
    allowed_literals = allowed_literals or set()
    if ref in allowed_literals:
        return
    if not isinstance(ref, str):
        errors.append(f"{context}: ref must be string, got {type(ref).__name__}")
        return
    if "*" in ref:
        errors.append(f"{context}: wildcard ref is not allowed: {ref}")
        return
    if ref.startswith("role:"):
        for role in ref.replace("role:", "").split("|"):
            ensure_ref(errors, ids, f"role.{role}", context)
        return
    if ref not in ids:
        errors.append(f"{context}: missing ref {ref}")


def ensure_refs(errors: list[str], ids: dict[str, str], refs: Any, context: str, allowed_literals: set[Any] | None = None) -> None:
    for ref in refs or []:
        ensure_ref(errors, ids, ref, context, allowed_literals)


def validate_common_metadata(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str], warnings: list[str]) -> None:
    allowed_relations = {item.get("type") for item in snapshot.get("relation_type_registry", [])}
    missing_relations = set(RELATION_TYPES) - allowed_relations
    if missing_relations:
        errors.append(f"relation registry missing types: {', '.join(sorted(missing_relations))}")
    for section in ID_SECTIONS:
        for item in snapshot.get(section, []) or []:
            source_type = item.get("source_type")
            confidence = item.get("confidence")
            if source_type and source_type not in SOURCE_TYPES:
                errors.append(f"{item.get('id', section)}.source_type: invalid value {source_type}")
            if confidence and confidence not in CONFIDENCE_VALUES:
                errors.append(f"{item.get('id', section)}.confidence: invalid value {confidence}")
            if source_type == "DERIVED" and not confidence:
                errors.append(f"{item.get('id', section)}: DERIVED fact must have confidence")
            if source_type == "DERIVED" and confidence == "low":
                warnings.append(f"{item.get('id', section)}: low confidence derived fact")


def validate_modules(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str]) -> None:
    for module in snapshot.get("modules", []):
        context = module["id"]
        ensure_refs(errors, ids, module.get("depends_on"), f"{context}.depends_on")
        ensure_refs(errors, ids, module.get("used_by"), f"{context}.used_by")
        ensure_refs(errors, ids, module.get("entities"), f"{context}.entities")
        ensure_refs(errors, ids, module.get("services"), f"{context}.services")
        ensure_refs(errors, ids, module.get("api"), f"{context}.api")
        ensure_refs(errors, ids, module.get("frontend_routes"), f"{context}.frontend_routes")


def validate_entities(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str]) -> None:
    for entity in snapshot.get("entities", []):
        context = entity["id"]
        ensure_ref(errors, ids, entity.get("module"), f"{context}.module")
        ensure_refs(errors, ids, entity.get("relationships"), f"{context}.relationships")


def validate_relationships(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str]) -> None:
    for relationship in snapshot.get("relationships", []):
        context = relationship["id"]
        ensure_ref(errors, ids, relationship.get("from"), f"{context}.from")
        ensure_ref(errors, ids, relationship.get("to"), f"{context}.to")
        ensure_ref(errors, ids, relationship.get("owner"), f"{context}.owner")
        ensure_relation_type(errors, relationship.get("type"), context)


def validate_services(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str]) -> None:
    for service in snapshot.get("services", []):
        context = service["id"]
        ensure_ref(errors, ids, service.get("module"), f"{context}.module")
        ensure_refs(errors, ids, service.get("reads_entities"), f"{context}.reads_entities")
        ensure_refs(errors, ids, service.get("writes_entities"), f"{context}.writes_entities")
        ensure_refs(errors, ids, service.get("calls_services"), f"{context}.calls_services")
        ensure_refs(errors, ids, service.get("called_by"), f"{context}.called_by")


def validate_api(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str]) -> None:
    for endpoint in snapshot.get("api", []):
        context = endpoint["id"]
        ensure_ref(errors, ids, endpoint.get("module"), f"{context}.module")
        ensure_refs(errors, ids, endpoint.get("service_calls"), f"{context}.service_calls")
        ensure_refs(errors, ids, endpoint.get("reads_entities"), f"{context}.reads_entities")
        ensure_refs(errors, ids, endpoint.get("writes_entities"), f"{context}.writes_entities")
        permission = endpoint.get("permission")
        if permission and permission.startswith("permission."):
            ensure_ref(errors, ids, permission, f"{context}.permission")


def validate_routes_and_components(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str]) -> None:
    for route in snapshot.get("frontend_routes", []):
        context = route["id"]
        ensure_ref(errors, ids, route.get("module"), f"{context}.module")
        ensure_ref(errors, ids, route.get("required_permission"), f"{context}.required_permission", {None})
        ensure_refs(errors, ids, route.get("api_dependencies"), f"{context}.api_dependencies")
    for component in snapshot.get("frontend_components", []):
        context = component["id"]
        ensure_ref(errors, ids, component.get("module"), f"{context}.module")
        ensure_refs(errors, ids, component.get("reads"), f"{context}.reads")
        ensure_refs(errors, ids, component.get("mutations"), f"{context}.mutations")


def validate_rbac(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str], warnings: list[str]) -> None:
    for role in snapshot.get("roles", []):
        ensure_refs(errors, ids, role.get("permissions"), f"{role['id']}.permissions")
    for permission in snapshot.get("permissions", []):
        context = permission["id"]
        ensure_refs(errors, ids, permission.get("roles"), f"{context}.roles")
        ensure_refs(errors, ids, permission.get("api"), f"{context}.api")
        ensure_refs(errors, ids, permission.get("routes"), f"{context}.routes")
    for actor in snapshot.get("actors", []):
        ensure_ref(errors, ids, actor.get("represented_by_role"), f"{actor['id']}.represented_by_role")
    for permission in snapshot.get("permissions", []):
        for role in permission.get("roles", []) or []:
            role_obj = next((item for item in snapshot.get("roles", []) if item.get("id") == role), None)
            if role_obj and permission["id"] not in (role_obj.get("permissions") or []):
                warnings.append(f"{permission['id']}: role mismatch for {role}")


def validate_use_cases(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str], warnings: list[str]) -> None:
    for use_case in snapshot.get("use_cases", []):
        context = use_case["id"]
        actor_refs = use_case.get("actors") or use_case.get("actor_roles")
        ensure_refs(errors, ids, actor_refs, f"{context}.actors")
        ensure_refs(errors, ids, use_case.get("entry_points"), f"{context}.entry_points")
        ensure_refs(errors, ids, use_case.get("api"), f"{context}.api")
        ensure_refs(errors, ids, use_case.get("services"), f"{context}.services")
        ensure_refs(errors, ids, use_case.get("reads_entities"), f"{context}.reads_entities")
        ensure_refs(errors, ids, use_case.get("writes_entities"), f"{context}.writes_entities")
        ensure_refs(errors, ids, use_case.get("required_permissions"), f"{context}.required_permissions")
        ensure_refs(errors, ids, use_case.get("notifications"), f"{context}.notifications")
        if not actor_refs:
            warnings.append(f"{context}: use case has no actors")


def validate_processes(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str], warnings: list[str]) -> None:
    for process in snapshot.get("business_processes", []):
        context = process["id"]
        ensure_ref(errors, ids, process.get("use_case"), f"{context}.use_case", {None})
        if not process.get("use_case"):
            warnings.append(f"{context}: process is not linked to use case")
        for step in process.get("steps", []) or []:
            ensure_ref(errors, ids, step.get("ref"), f"{context}.steps[{step.get('order')}].ref", {None})
    for flow in snapshot.get("data_flows", []):
        context = flow["id"]
        ensure_refs(errors, ids, flow.get("modules"), f"{context}.modules")
        ensure_refs(errors, ids, flow.get("entities"), f"{context}.entities")
        ensure_refs(errors, ids, flow.get("services"), f"{context}.services")
        for step in flow.get("steps", []) or []:
            ensure_ref(errors, ids, step.get("ref"), f"{context}.steps[{step.get('order')}].ref")


def validate_states(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str]) -> None:
    states_by_id = {state["id"]: state for state in snapshot.get("states", [])}
    entities_by_id = {entity["id"]: entity for entity in snapshot.get("entities", [])}
    state_values = set()
    for stateful in snapshot.get("stateful_entities", []):
        context = stateful["id"]
        ensure_ref(errors, ids, stateful.get("entity"), f"{context}.entity")
        if stateful.get("state_kind") and stateful.get("state_kind") not in STATE_KINDS:
            errors.append(f"{context}.state_kind: invalid value {stateful.get('state_kind')}")
    for state in snapshot.get("states", []):
        context = state["id"]
        ensure_ref(errors, ids, state.get("entity"), f"{context}.entity")
        if state.get("state_kind") not in STATE_KINDS:
            errors.append(f"{context}.state_kind: invalid value {state.get('state_kind')}")
        validate_state_representation(state, entities_by_id.get(state.get("entity")), errors)
        representation = state.get("representation") or {}
        key = (state.get("entity"), state.get("state_kind"), representation.get("field"), representation.get("value") or representation.get("condition"))
        if key in state_values:
            errors.append(f"{context}: duplicate state value for entity/kind")
        state_values.add(key)
    for transition in snapshot.get("transitions", []):
        context = transition["id"]
        ensure_ref(errors, ids, transition.get("entity"), f"{context}.entity")
        ensure_ref(errors, ids, transition.get("from"), f"{context}.from")
        ensure_ref(errors, ids, transition.get("to"), f"{context}.to")
        ensure_ref(errors, ids, transition.get("business_rule"), f"{context}.business_rule", {None})
        ensure_ref(errors, ids, transition.get("service"), f"{context}.service", {None})
        ensure_refs(errors, ids, transition.get("api"), f"{context}.api")
        ensure_refs(errors, ids, transition.get("caused_by"), f"{context}.caused_by")
        if transition.get("transition_kind") not in TRANSITION_KINDS:
            errors.append(f"{context}.transition_kind: invalid value {transition.get('transition_kind')}")
        if transition.get("trigger_type") not in TRIGGER_TYPES:
            errors.append(f"{context}.trigger_type: invalid value {transition.get('trigger_type')}")
        from_state = states_by_id.get(transition.get("from"))
        to_state = states_by_id.get(transition.get("to"))
        if from_state and from_state.get("entity") != transition.get("entity"):
            errors.append(f"{context}.from: state does not belong to transition entity")
        if to_state and to_state.get("entity") != transition.get("entity"):
            errors.append(f"{context}.to: state does not belong to transition entity")
        if from_state and to_state and from_state.get("entity") != to_state.get("entity"):
            errors.append(f"{context}: transition crosses entity state machines")
    for group in snapshot.get("derived_state_groups", []):
        context = group["id"]
        ensure_ref(errors, ids, group.get("entity"), f"{context}.entity")
        ensure_refs(errors, ids, group.get("source"), f"{context}.source")
        if group.get("state_kind") not in STATE_KINDS:
            errors.append(f"{context}.state_kind: invalid value {group.get('state_kind')}")


def validate_state_representation(state: dict[str, Any], entity: dict[str, Any] | None, errors: list[str]) -> None:
    context = state["id"]
    representation = state.get("representation")
    if not isinstance(representation, dict):
        errors.append(f"{context}.representation: missing object")
        return
    field_name = representation.get("field")
    fields = entity.get("fields", []) if entity else []
    field = next((item for item in fields if item.get("name") == field_name), None)
    if not field:
        errors.append(f"{context}.representation.field: missing entity field {field_name}")
        return
    if state.get("state_kind") == "PERSISTED_STATE" and "value" not in representation:
        errors.append(f"{context}.representation.value: required for persisted state")
    if state.get("state_kind") == "DERIVED_STATE" and "value" not in representation and "condition" not in representation:
        errors.append(f"{context}.representation: derived state requires value or condition")
    if "condition" in representation and representation["condition"] not in {"true", "false"}:
        errors.append(f"{context}.representation.condition: expected true/false")
    enum_values = enum_values_for(entity, str(field_name)) if entity else []
    if "value" in representation and enum_values and representation["value"] not in enum_values:
        errors.append(f"{context}.representation.value: {representation['value']} is not declared for {field_name}")


def enum_values_for(entity: dict[str, Any] | None, field_name: str) -> list[str]:
    if not entity:
        return []
    values = entity.get("enum_values")
    if isinstance(values, list):
        return [str(item) for item in values]
    if isinstance(values, dict):
        by_field = {
            "status": ["ScheduleEventStatus"],
            "event_type": ["ScheduleEventType"],
            "attendance_status": ["AttendanceStatus"],
        }
        keys = by_field.get(field_name, [])
        result = []
        for key in keys:
            result.extend(str(item) for item in values.get(key, []) or [])
        return result
    return []


def validate_interactions(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str]) -> None:
    for interaction in snapshot.get("interactions", []):
        context = interaction["id"]
        ensure_ref(errors, ids, interaction.get("use_case"), f"{context}.use_case", {None})
        ensure_ref(errors, ids, interaction.get("process"), f"{context}.process")
        ensure_refs(errors, ids, interaction.get("participants"), f"{context}.participants")
        for message in interaction.get("messages", []) or []:
            ensure_ref(errors, ids, message.get("from"), f"{context}.messages[{message.get('order')}].from")
            ensure_ref(errors, ids, message.get("to"), f"{context}.messages[{message.get('order')}].to")


def validate_data_model(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str]) -> None:
    for table in snapshot.get("data_tables", []):
        ensure_ref(errors, ids, table.get("entity"), f"{table['id']}.entity")
    for mapping in snapshot.get("entity_table_mappings", []):
        ensure_ref(errors, ids, mapping.get("from"), f"{mapping['id']}.from")
        ensure_ref(errors, ids, mapping.get("to"), f"{mapping['id']}.to")
        ensure_relation_type(errors, mapping.get("type"), mapping["id"])


def validate_deployments(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str]) -> None:
    for component in snapshot.get("components", []):
        context = component["id"]
        ensure_refs(errors, ids, component.get("contains_services"), f"{context}.contains_services")
        ensure_refs(errors, ids, component.get("contains_routes"), f"{context}.contains_routes")
        ensure_refs(errors, ids, component.get("requires_api"), f"{context}.requires_api")
        ensure_refs(errors, ids, component.get("exposes_api"), f"{context}.exposes_api")
        ensure_refs(errors, ids, component.get("contains_tables"), f"{context}.contains_tables")
    for deployment in snapshot.get("component_deployments", []):
        ensure_ref(errors, ids, deployment.get("from"), f"{deployment['id']}.from")
        ensure_ref(errors, ids, deployment.get("to"), f"{deployment['id']}.to")
        ensure_relation_type(errors, deployment.get("type"), deployment["id"])


def validate_sources_of_truth(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str], warnings: list[str]) -> None:
    concepts = Counter()
    for source in snapshot.get("sources_of_truth", []):
        context = source.get("id") or source.get("concept")
        concepts[source.get("concept")] += 1
        source_ref = source.get("source")
        if isinstance(source_ref, dict):
            ensure_ref(errors, ids, source_ref.get("ref"), f"{context}.source.ref")
        else:
            ensure_ref(errors, ids, source_ref, f"{context}.source")
        ensure_refs(errors, ids, source.get("consumers"), f"{context}.consumers", {None})
        if source.get("conflicts"):
            warnings.append(f"{context}: source-of-truth conflict declared")
    for concept, count in concepts.items():
        if concept and count > 1:
            matching = [source for source in snapshot.get("sources_of_truth", []) if source.get("concept") == concept]
            if not any(source.get("conflicts") for source in matching):
                errors.append(f"source_of_truth.{concept}: duplicate source without conflict")


def validate_traceability(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str]) -> None:
    for trace in snapshot.get("traceability", []):
        context = trace["id"]
        ensure_ref(errors, ids, trace.get("use_case"), f"{context}.use_case", {None})
        ensure_ref(errors, ids, trace.get("process"), f"{context}.process", {None})
        ensure_ref(errors, ids, trace.get("interaction"), f"{context}.interaction", {None})
        for key in ["entities", "services", "api", "permissions", "tables"]:
            ensure_refs(errors, ids, trace.get(key), f"{context}.{key}")


def validate_technical_debt(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str]) -> None:
    for debt in snapshot.get("technical_debt", []):
        ensure_refs(errors, ids, debt.get("affected_nodes"), f"{debt['id']}.affected_nodes")
    for edge in snapshot.get("impact_edges", []):
        ensure_ref(errors, ids, edge.get("from"), "impact_edges.from")
        ensure_ref(errors, ids, edge.get("to"), "impact_edges.to")
        ensure_relation_type(errors, edge.get("type"), f"{edge.get('from')}->{edge.get('to')}")


def validate_dependency_model(snapshot: dict[str, Any], ids: dict[str, str], errors: list[str]) -> None:
    module_ids = {module["id"] for module in snapshot.get("modules", []) or []}
    observed_ids = {item["id"] for item in snapshot.get("observed_interactions", []) or []}

    for interaction in snapshot.get("observed_interactions", []):
        context = interaction["id"]
        ensure_ref(errors, ids, interaction.get("from"), f"{context}.from")
        ensure_ref(errors, ids, interaction.get("to"), f"{context}.to")
        ensure_ref(errors, ids, interaction.get("source"), f"{context}.source")
        ensure_ref(errors, ids, interaction.get("target"), f"{context}.target")
        ensure_relation_type(errors, interaction.get("interaction_type"), context)
        if interaction.get("from") not in module_ids or interaction.get("to") not in module_ids:
            errors.append(f"{context}: observed interaction must connect modules")

    for dependency in snapshot.get("cross_module_dependencies", []):
        context = dependency["id"]
        ensure_ref(errors, ids, dependency.get("from"), f"{context}.from")
        ensure_ref(errors, ids, dependency.get("to"), f"{context}.to")
        ensure_refs(errors, ids, dependency.get("via_services"), f"{context}.via_services")
        ensure_refs(errors, ids, dependency.get("via_entities"), f"{context}.via_entities")
        ensure_refs(errors, ids, dependency.get("observed_interactions"), f"{context}.observed_interactions")
        ensure_relation_type(errors, dependency.get("type"), context)
        if dependency.get("classification") not in DEPENDENCY_CLASSIFICATIONS:
            errors.append(f"{context}.classification: invalid value {dependency.get('classification')}")
        if dependency.get("importance") not in DEPENDENCY_IMPORTANCE:
            errors.append(f"{context}.importance: invalid value {dependency.get('importance')}")
        if dependency.get("default_visibility") not in DEPENDENCY_VISIBILITY:
            errors.append(f"{context}.default_visibility: invalid value {dependency.get('default_visibility')}")
        missing_observed = [item for item in dependency.get("observed_interactions", []) or [] if item not in observed_ids]
        if missing_observed:
            errors.append(f"{context}.observed_interactions: missing observed refs {', '.join(missing_observed)}")

    dependency_ids = {item["id"] for item in snapshot.get("cross_module_dependencies", []) or []}
    for cycle in snapshot.get("architectural_cycles", []) or []:
        context = cycle["id"]
        if cycle.get("type") != "CIRCULAR_DEPENDENCY":
            errors.append(f"{context}.type: invalid value {cycle.get('type')}")
        ensure_refs(errors, ids, cycle.get("modules"), f"{context}.modules")
        missing_deps = [item for item in cycle.get("dependencies", []) or [] if item not in dependency_ids]
        if missing_deps:
            errors.append(f"{context}.dependencies: missing dependency refs {', '.join(missing_deps)}")


def ensure_relation_type(errors: list[str], relation_type: Any, context: str) -> None:
    if relation_type and relation_type not in RELATION_TYPES:
        errors.append(f"{context}: invalid relation type {relation_type}")


def main() -> dict[str, Any]:
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    report = validate(snapshot)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not report["valid"]:
        print("Snapshot validation failed:")
        for error in report["errors"]:
            print(f"- {error}")
        raise SystemExit(1)

    stats = report["statistics"]
    print(
        "Snapshot validation passed: "
        f"{stats['modules']} modules, "
        f"{stats['entities']} entities, "
        f"{stats['api']} api endpoints."
    )
    if report["warnings"]:
        print(f"Snapshot validation warnings: {len(report['warnings'])}")
    return report


if __name__ == "__main__":
    main()
