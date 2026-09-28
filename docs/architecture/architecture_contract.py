from __future__ import annotations

from typing import Any


SCHEMA_VERSION = 2
MODEL_CONTRACT_VERSION = 1

ARCHITECTURE_OBJECT_TYPES = [
    "Module",
    "Actor",
    "UseCase",
    "Entity",
    "State",
    "Transition",
    "BusinessRule",
    "BusinessProcess",
    "Interaction",
    "Service",
    "APIEndpoint",
    "DataTable",
    "Component",
    "DeploymentNode",
    "Permission",
    "Role",
    "ExternalSystem",
    "SourceOfTruth",
    "TechnicalDebt",
]

RELATION_TYPES = [
    "contains",
    "belongs_to",
    "reads",
    "writes",
    "calls",
    "exposes",
    "depends_on",
    "performs",
    "initiates",
    "executes",
    "transitions_to",
    "persisted_as",
    "deployed_on",
    "requires_permission",
    "represented_by_role",
    "aggregates",
    "produces",
    "consumes",
    "observes",
    "reads_writes",
    "source_of_truth",
    "permission_for",
    "renders",
    "one_to_one",
    "one_to_many",
    "many_to_one",
    "many_to_many",
]

SOURCE_TYPES = ["EXTRACTED", "DERIVED", "DECLARED"]
CONFIDENCE_VALUES = ["high", "medium", "low"]


def apply_v2_contract(snapshot: dict[str, Any]) -> dict[str, Any]:
    snapshot["schema_version"] = SCHEMA_VERSION
    snapshot["model_contract_version"] = MODEL_CONTRACT_VERSION
    snapshot["metamodel"] = {
        "object_types": ARCHITECTURE_OBJECT_TYPES,
        "relation_types": RELATION_TYPES,
        "source_types": SOURCE_TYPES,
        "confidence_values": CONFIDENCE_VALUES,
        "source_of_truth": "docs/architecture/architecture_snapshot.json",
    }
    snapshot["relation_type_registry"] = [{"type": relation_type} for relation_type in RELATION_TYPES]

    annotate_existing_facts(snapshot)
    snapshot["actors"] = build_actors(snapshot)
    snapshot["states"] = build_states(snapshot)
    snapshot["transitions"] = build_transitions(snapshot)
    snapshot["data_tables"] = build_data_tables(snapshot)
    snapshot["entity_table_mappings"] = build_entity_table_mappings(snapshot)
    snapshot["components"] = build_components(snapshot)
    snapshot["deployment_nodes"] = build_deployment_nodes(snapshot)
    snapshot["component_deployments"] = build_component_deployments(snapshot)
    snapshot["business_processes"] = build_business_processes(snapshot)
    snapshot["interactions"] = build_interactions(snapshot)
    snapshot["traceability"] = build_traceability(snapshot)
    snapshot["model_readiness"] = build_model_readiness(snapshot)
    snapshot["validation_report"] = {
        "valid": None,
        "errors": [],
        "warnings": [],
        "statistics": {},
    }
    return snapshot


def annotate_existing_facts(snapshot: dict[str, Any]) -> None:
    for section in [
        "modules",
        "entities",
        "relationships",
        "services",
        "api",
        "frontend_routes",
        "frontend_components",
        "roles",
        "permissions",
    ]:
        for item in snapshot.get(section, []):
            item.setdefault("source_type", "EXTRACTED")
            item.setdefault("confidence", "high")
            evidence = evidence_from_item(item)
            if evidence:
                item.setdefault("evidence", evidence)

    for item in snapshot.get("business_rules", []):
        item.setdefault("source_type", "EXTRACTED")
        item.setdefault("confidence", "high")
        item.setdefault("reads", item.get("reads_entities", []))
        item.setdefault("writes", item.get("writes_entities", []))
        evidence = evidence_from_item(item)
        if evidence:
            item.setdefault("evidence", evidence)

    role_to_actor = {role.get("id"): f"actor.{str(role.get('id', '')).replace('role.', '')}" for role in snapshot.get("roles", [])}
    api_permissions = {endpoint.get("id"): endpoint.get("permission") for endpoint in snapshot.get("api", [])}
    for item in snapshot.get("use_cases", []):
        item.setdefault("source_type", "DECLARED")
        item.setdefault("confidence", "medium")
        item.setdefault("actors", [role_to_actor[role] for role in item.get("actor_roles", []) or [] if role in role_to_actor])
        permissions = set(item.get("required_permissions", []) or [])
        permissions.update(api_permissions.get(api) for api in item.get("api", []) or [])
        item["required_permissions"] = sorted(permission for permission in permissions if str(permission).startswith("permission."))

    for item in snapshot.get("cross_module_dependencies", []):
        item.setdefault("source_type", "DERIVED")
        item.setdefault("confidence", "high" if item.get("risk") in {"high", "critical"} else "medium")
        item.setdefault("evidence", evidence_from_dependency(item))

    normalize_sources_of_truth(snapshot)


def build_actors(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    actors = []
    for role in snapshot.get("roles", []):
        role_name = str(role.get("name") or role["id"].replace("role.", ""))
        actor_id = f"actor.{role['id'].replace('role.', '')}"
        actors.append(
            {
                "id": actor_id,
                "name": role_name.title(),
                "name_ru": actor_name_ru(role_name),
                "represented_by_role": role["id"],
                "source_type": "DERIVED",
                "confidence": "high",
            }
        )
    return actors


def build_states(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    states = []
    for entity in snapshot.get("entities", []):
        for state in entity.get("enum_values", []) or []:
            states.append(
                {
                    "id": f"state.{entity['id'].replace('entity.', '')}.{state}",
                    "entity": entity["id"],
                    "name": state,
                    "source_type": "EXTRACTED",
                    "confidence": "high",
                    "evidence": evidence_from_item(entity),
                }
            )
    return states


def build_transitions(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    states = {state["id"] for state in build_states(snapshot)}
    candidates = [
        ("transition.membership.active_finished", "entity.membership", "active", "finished", "remaining_lessons == 0", "rule.membership.complete_zero_lessons"),
        ("transition.membership.active_expired", "entity.membership", "active", "expired", "end_date < today", "rule.membership.active_definition"),
        ("transition.membership.active_frozen", "entity.membership", "active", "frozen", "freeze action", "rule.membership.active_definition"),
        ("transition.membership.frozen_active", "entity.membership", "frozen", "active", "unfreeze action", "rule.membership.active_definition"),
        ("transition.membership.active_cancelled", "entity.membership", "active", "cancelled", "cancel action", "rule.membership.active_definition"),
        ("transition.practice_rental.active_cancelled", "entity.practice_rental", "active", "cancelled", "cancel practice rental", "rule.practice.not_visit"),
        ("transition.extra_expense.active_cancelled", "entity.extra_expense", "active", "cancelled", "cancel extra expense", "rule.extra_expenses.finance_inclusion"),
    ]
    transitions = []
    rules = {rule["id"] for rule in snapshot.get("business_rules", [])}
    for transition_id, entity_id, from_state, to_state, trigger, rule_id in candidates:
        from_id = f"state.{entity_id.replace('entity.', '')}.{from_state}"
        to_id = f"state.{entity_id.replace('entity.', '')}.{to_state}"
        if from_id not in states or to_id not in states:
            continue
        transitions.append(
            {
                "id": transition_id,
                "entity": entity_id,
                "from": from_id,
                "to": to_id,
                "trigger": trigger,
                "business_rule": rule_id if rule_id in rules else None,
                "source_type": "DERIVED",
                "confidence": "medium",
            }
        )
    return transitions


def build_data_tables(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    tables = []
    seen = set()
    for entity in snapshot.get("entities", []):
        table = entity.get("table")
        if not table or table in seen:
            continue
        seen.add(table)
        fields = entity.get("fields", []) or []
        tables.append(
            {
                "id": f"table.{table}",
                "name": table,
                "entity": entity["id"],
                "columns": fields,
                "primary_key": [field["name"] for field in fields if field.get("type") == "primary_key"],
                "foreign_keys": [field for field in fields if field.get("foreign_key")],
                "constraints": entity.get("constraints", []),
                "indexes": entity.get("indexes", []),
                "source_type": "EXTRACTED",
                "confidence": "high",
                "evidence": evidence_from_item(entity),
            }
        )
    return tables


def build_entity_table_mappings(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    mappings = []
    for entity in snapshot.get("entities", []):
        table = entity.get("table")
        if table:
            mappings.append(
                {
                    "id": f"relation.{entity['id'].replace('.', '_')}.persisted_as.{table}",
                    "from": entity["id"],
                    "to": f"table.{table}",
                    "type": "persisted_as",
                    "source_type": "EXTRACTED",
                    "confidence": "high",
                    "evidence": evidence_from_item(entity),
                }
            )
    return mappings


def build_components(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    services = [service["id"] for service in snapshot.get("services", [])]
    api = [endpoint["id"] for endpoint in snapshot.get("api", [])]
    routes = [route["id"] for route in snapshot.get("frontend_routes", [])]
    return [
        {
            "id": "component.frontend",
            "name": "React frontend",
            "type": "application",
            "contains_routes": routes,
            "requires_api": api,
            "source_type": "EXTRACTED",
            "confidence": "high",
            "evidence": [{"file": "client", "symbol": "Vite React application"}],
        },
        {
            "id": "component.backend",
            "name": "FastAPI backend",
            "type": "application",
            "contains_services": services,
            "exposes_api": api,
            "source_type": "EXTRACTED",
            "confidence": "high",
            "evidence": [{"file": "server/app/main.py", "symbol": "app"}],
        },
        {
            "id": "component.database",
            "name": "SQLite database",
            "type": "database",
            "contains_tables": [table["id"] for table in build_data_tables(snapshot)],
            "source_type": "EXTRACTED",
            "confidence": "high",
            "evidence": [{"file": "server/app/database.py", "symbol": "DATABASE_URL"}],
        },
    ]


def build_deployment_nodes(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"id": "deployment.vps", "name": "VPS host", "type": "host", "source_type": "DECLARED", "confidence": "medium", "evidence": [{"file": "docker-compose.prod.yml", "symbol": "services"}]},
        {"id": "deployment.frontend_container", "name": "Frontend container", "type": "container", "source_type": "EXTRACTED", "confidence": "high", "evidence": [{"file": "docker-compose.prod.yml", "symbol": "frontend"}]},
        {"id": "deployment.backend_container", "name": "Backend container", "type": "container", "source_type": "EXTRACTED", "confidence": "high", "evidence": [{"file": "docker-compose.prod.yml", "symbol": "backend"}]},
        {"id": "deployment.sqlite_volume", "name": "SQLite Docker volume", "type": "volume", "source_type": "EXTRACTED", "confidence": "high", "evidence": [{"file": "docker-compose.prod.yml", "symbol": "backend-data"}]},
        {"id": "deployment.caddy_container", "name": "Caddy reverse proxy", "type": "container", "source_type": "EXTRACTED", "confidence": "high", "evidence": [{"file": "deploy/Caddyfile", "symbol": "reverse_proxy"}]},
    ]


def build_component_deployments(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"id": "relation.component_frontend.deployed_on.frontend_container", "from": "component.frontend", "to": "deployment.frontend_container", "type": "deployed_on", "source_type": "EXTRACTED", "confidence": "high"},
        {"id": "relation.component_backend.deployed_on.backend_container", "from": "component.backend", "to": "deployment.backend_container", "type": "deployed_on", "source_type": "EXTRACTED", "confidence": "high"},
        {"id": "relation.component_database.deployed_on.sqlite_volume", "from": "component.database", "to": "deployment.sqlite_volume", "type": "deployed_on", "source_type": "EXTRACTED", "confidence": "high"},
    ]


def build_business_processes(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    processes = []
    flow_use_case = {
        "flow.schedule_completion": "use_case.schedule.complete_event",
        "flow.membership_completion": "use_case.membership.issue",
        "flow.course_recurrence": "use_case.schedule.create_event",
        "flow.practice_to_finance": "use_case.practice.create_rental",
        "flow.extra_expense_to_finance": "use_case.extra_expense.create",
        "flow.monthly_expense_to_payment_obligation": "use_case.payment_obligation.pay",
        "flow.payment_obligation_to_notifications": "use_case.payment_obligation.pay",
        "flow.payment_obligation_to_finance": "use_case.finance.monthly_report",
    }
    use_case_ids = {item["id"] for item in snapshot.get("use_cases", [])}
    for flow in snapshot.get("data_flows", []):
        flow_suffix = flow["id"].replace("flow.", "")
        matching_use_case = flow_use_case.get(flow["id"])
        if matching_use_case not in use_case_ids:
            matching_use_case = None
        processes.append(
            {
                "id": f"process.{flow_suffix}",
                "name": flow.get("name", flow["id"]),
                "use_case": matching_use_case,
                "steps": [
                    {
                        "id": f"process.{flow_suffix}.step.{step.get('order', index + 1)}",
                        "order": step.get("order", index + 1),
                        "type": step.get("type", "action"),
                        "name": step.get("action", ""),
                        "ref": step.get("ref"),
                    }
                    for index, step in enumerate(flow.get("steps", []) or [])
                ],
                "source_type": "DERIVED",
                "confidence": "medium",
            }
        )
    return processes


def build_interactions(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    interactions = []
    for process in build_business_processes(snapshot):
        participants = ["component.frontend"]
        for step in process.get("steps", []):
            ref = step.get("ref")
            if ref:
                participants.append(ref)
        unique_participants = list(dict.fromkeys(participants))
        messages = []
        for index in range(len(unique_participants) - 1):
            messages.append(
                {
                    "order": index + 1,
                    "from": unique_participants[index],
                    "to": unique_participants[index + 1],
                    "type": "sync",
                    "action": "executes next process step",
                }
            )
        interactions.append(
            {
                "id": f"interaction.{process['id'].replace('process.', '')}",
                "use_case": process.get("use_case"),
                "process": process["id"],
                "participants": unique_participants,
                "messages": messages,
                "source_type": "DERIVED",
                "confidence": "medium",
            }
        )
    return interactions


def build_traceability(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    processes = build_business_processes(snapshot)
    interactions = build_interactions(snapshot)
    by_process = {interaction["process"]: interaction for interaction in interactions}
    records = []
    for process in processes:
        refs = [step.get("ref") for step in process.get("steps", []) if step.get("ref")]
        records.append(
            {
                "id": f"trace.{process['id'].replace('process.', '')}",
                "use_case": process.get("use_case"),
                "process": process["id"],
                "interaction": by_process.get(process["id"], {}).get("id"),
                "entities": [ref for ref in refs if str(ref).startswith("entity.")],
                "services": [ref for ref in refs if str(ref).startswith("service.")],
                "api": [ref for ref in refs if str(ref).startswith("api.")],
                "permissions": [],
                "tables": [],
            }
        )
    return records


def build_model_readiness(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    relationships = snapshot.get("relationships", [])
    return [
        readiness("system_map", "System Map", bool(snapshot.get("modules") and snapshot.get("cross_module_dependencies")), "Module dependencies available."),
        readiness("domain_model", "Domain Model", bool(snapshot.get("entities") and relationships), "Entities and relationships available."),
        readiness("use_case_model", "Use Case Model", bool(snapshot.get("use_cases") and snapshot.get("actors")), "Use cases have actor mapping."),
        readiness("activity_model", "Activity Model", bool(snapshot.get("business_processes")), "Business processes are derived from data flows."),
        readiness("state_model", "State Model", bool(snapshot.get("states")), "States are extracted from enum values; transitions are partial."),
        readiness("sequence_model", "Sequence Model", bool(snapshot.get("interactions")), "Interactions are derived from business processes."),
        readiness("data_model", "Data Model", bool(snapshot.get("data_tables")), "Data tables are extracted from entities with table names."),
        readiness("component_model", "Component Model", bool(snapshot.get("components")), "Coarse application components are confirmed from repo structure."),
        readiness("deployment_model", "Deployment Model", bool(snapshot.get("deployment_nodes")), "Docker/Caddy deployment nodes are confirmed from repo config."),
    ]


def readiness(model_id: str, name: str, ready: bool, note: str) -> dict[str, Any]:
    return {"id": f"readiness.{model_id}", "model": model_id, "name": name, "status": "ready" if ready else "missing", "note": note}


def normalize_sources_of_truth(snapshot: dict[str, Any]) -> None:
    ids = {item.get("id") for section in ["entities", "services", "modules", "api", "business_rules"] for item in snapshot.get(section, [])}
    for index, source in enumerate(snapshot.get("sources_of_truth", []) or []):
        concept = str(source.get("concept") or f"source.{index}")
        source.setdefault("id", f"sot.{slug(concept)}")
        source.setdefault("source_type", "DECLARED")
        source.setdefault("confidence", source.get("confidence") or "medium")
        current = source.get("source")
        if isinstance(current, dict):
            continue
        if current in ids:
            source["source"] = {"type": "architecture_ref", "ref": current}
        else:
            source["source"] = {"type": "expression", "ref": None, "expression": current}


def evidence_from_item(item: dict[str, Any]) -> list[dict[str, str]]:
    file_name = item.get("source_file") or item.get("router_file")
    symbol = item.get("source_symbol") or item.get("handler") or item.get("name") or item.get("id")
    if not file_name:
        return []
    return [{"file": str(file_name), "symbol": str(symbol)}]


def evidence_from_dependency(item: dict[str, Any]) -> list[dict[str, str]]:
    services = item.get("via_services", []) or []
    entities = item.get("via_entities", []) or []
    evidence = [{"file": str(ref), "symbol": str(item.get("type", ""))} for ref in [*services, *entities]]
    return evidence


def actor_name_ru(role_name: str) -> str:
    return {"admin": "Администратор", "operator": "Оператор", "finance": "Финансист"}.get(role_name, role_name.title())


def slug(value: str) -> str:
    result = []
    for char in value.lower():
        if char.isalnum():
            result.append(char)
        elif result and result[-1] != "_":
            result.append("_")
    return "".join(result).strip("_") or "unknown"
