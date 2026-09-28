from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


SNAPSHOT_PATH = Path(__file__).with_name("architecture_snapshot.json")
OVERRIDES_PATH = Path(__file__).with_name("dependency-overrides.json")

CLASSIFICATIONS = {"DOMAIN", "APPLICATION", "DATA", "CONTROL", "OBSERVABILITY", "UI_COMPOSITION", "INFRASTRUCTURE"}
IMPORTANCE = {"PRIMARY", "SECONDARY", "SUPPORTING"}
VISIBILITY = {"MAIN", "DETAIL", "HIDDEN"}
SUPPORTING_CLASSES = {"CONTROL", "OBSERVABILITY", "INFRASTRUCTURE", "UI_COMPOSITION"}
MAIN_DEPENDENCY_IDS = {
    "dependency.schedule_membership",
    "dependency.finance_visits",
    "dependency.finance_memberships",
    "dependency.practice_finance",
    "dependency.extra_expenses_finance",
}


def apply_dependency_model(snapshot: dict[str, Any]) -> dict[str, Any]:
    overrides = load_overrides()
    context = build_context(snapshot)
    observed = build_observed_interactions(snapshot, context)
    canonical = build_canonical_dependencies(snapshot, observed, overrides)
    cycles = find_architectural_cycles(canonical)

    snapshot["observed_interactions"] = observed
    snapshot["cross_module_dependencies"] = canonical
    snapshot["architectural_cycles"] = cycles
    snapshot["dependency_metrics"] = build_dependency_metrics(snapshot, observed, canonical, cycles)
    return snapshot


def load_overrides() -> dict[str, dict[str, Any]]:
    if not OVERRIDES_PATH.exists():
        return {}
    return json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))


def build_context(snapshot: dict[str, Any]) -> dict[str, Any]:
    owner_by_id: dict[str, str] = {}
    item_by_id: dict[str, dict[str, Any]] = {}
    for section in ["modules", "entities", "services", "api", "frontend_routes", "frontend_components", "business_rules", "use_cases"]:
        for item in snapshot.get(section, []) or []:
            item_by_id[item["id"]] = item
            if item.get("module"):
                owner_by_id[item["id"]] = item["module"]
    for module in snapshot.get("modules", []) or []:
        for key in ["entities", "services", "api", "frontend_routes"]:
            for item_id in module.get(key, []) or []:
                owner_by_id[item_id] = module["id"]
    return {"owner_by_id": owner_by_id, "item_by_id": item_by_id}


def build_observed_interactions(snapshot: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    observed: list[dict[str, Any]] = []
    for section in ["services", "api", "frontend_routes", "frontend_components", "business_rules", "use_cases"]:
        for item in snapshot.get(section, []) or []:
            source_module = item.get("module") or context["owner_by_id"].get(item["id"])
            if not source_module:
                continue
            for ref_key, interaction_type in interaction_fields():
                for ref in item.get(ref_key, []) or []:
                    target_module = context["owner_by_id"].get(ref)
                    if not target_module or target_module == source_module:
                        continue
                    observed.append(observed_interaction(item, ref, ref_key, interaction_type, source_module, target_module))
    for relationship in snapshot.get("relationships", []) or []:
        source_module = context["owner_by_id"].get(relationship.get("from"))
        target_module = context["owner_by_id"].get(relationship.get("to"))
        if source_module and target_module and source_module != target_module:
            observed.append(
                observed_interaction(
                    relationship,
                    str(relationship.get("to")),
                    "relationship.to",
                    "reads",
                    source_module,
                    target_module,
                )
            )
    return sorted(dedupe_observed(observed), key=lambda item: (item["from"], item["to"], item["source"], item["target"], item["interaction_type"]))


def interaction_fields() -> list[tuple[str, str]]:
    return [
        ("reads_entities", "reads"),
        ("writes_entities", "writes"),
        ("reads", "reads"),
        ("writes", "writes"),
        ("calls_services", "calls"),
        ("service_calls", "calls"),
        ("api_dependencies", "calls"),
        ("entities", "reads"),
        ("services", "calls"),
        ("api", "calls"),
        ("entry_points", "renders"),
    ]


def observed_interaction(item: dict[str, Any], ref: str, ref_key: str, interaction_type: str, source_module: str, target_module: str) -> dict[str, Any]:
    source_id = item["id"]
    interaction_id = f"observed.{slug(source_module)}.{slug(target_module)}.{slug(source_id)}.{slug(ref)}.{interaction_type}"
    return {
        "id": interaction_id,
        "from": source_module,
        "to": target_module,
        "source": source_id,
        "target": ref,
        "interaction_type": interaction_type,
        "observed_field": ref_key,
        "evidence": evidence_from_item(item, ref),
        "source_type": "DERIVED",
        "confidence": "high" if interaction_type in {"writes", "calls"} else "medium",
    }


def dedupe_observed(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {}
    for item in items:
        by_id[item["id"]] = item
    return list(by_id.values())


def build_canonical_dependencies(snapshot: dict[str, Any], observed: list[dict[str, Any]], overrides: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    existing_by_pair = {(dep.get("from"), dep.get("to")): dep for dep in snapshot.get("cross_module_dependencies", []) or []}
    observed_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in observed:
        observed_by_pair[(item["from"], item["to"])].append(item)

    dependencies = []
    for pair in sorted(set(observed_by_pair) | set(existing_by_pair)):
        existing = existing_by_pair.get(pair)
        interactions = observed_by_pair.get(pair, [])
        if not interactions and not existing:
            continue
        dependency = canonical_dependency(pair, interactions, existing)
        apply_override(dependency, overrides)
        dependencies.append(dependency)
    return sorted(dependencies, key=lambda item: item["id"])


def canonical_dependency(pair: tuple[str, str], interactions: list[dict[str, Any]], existing: dict[str, Any] | None) -> dict[str, Any]:
    dep_id = existing.get("id") if existing else f"dependency.{slug(pair[0])}.{slug(pair[1])}"
    interaction_types = sorted({item["interaction_type"] for item in interactions} | ({existing.get("type")} if existing and existing.get("type") else set()))
    classification = classify_dependency(pair[0], pair[1], interaction_types, interactions, existing)
    importance = infer_importance(dep_id, pair[0], pair[1], classification, interaction_types)
    visibility = infer_visibility(classification, importance)
    confidence = infer_confidence(interactions, existing)
    reason = existing.get("reason") if existing else reason_for(pair[0], pair[1], classification, interaction_types)
    return {
        "id": dep_id,
        "from": pair[0],
        "to": pair[1],
        "type": strongest_type(interaction_types),
        "interaction_types": interaction_types,
        "classification": classification,
        "importance": importance,
        "default_visibility": visibility,
        "reason": reason,
        "evidence": merge_evidence(interactions, existing),
        "observed_interactions": [item["id"] for item in interactions],
        "via_services": sorted({ref for item in interactions for ref in [item["source"], item["target"]] if ref.startswith("service.")} | set(existing.get("via_services", []) if existing else [])),
        "via_entities": sorted({ref for item in interactions for ref in [item["source"], item["target"]] if ref.startswith("entity.")} | set(existing.get("via_entities", []) if existing else [])),
        "risk": existing.get("risk") if existing else risk_for(classification, importance),
        "source_type": "DERIVED",
        "confidence": confidence,
    }


def classify_dependency(source: str, target: str, types: list[str], interactions: list[dict[str, Any]], existing: dict[str, Any] | None) -> str:
    if "infrastructure" in source or "infrastructure" in target:
        return "INFRASTRUCTURE"
    if "auth" in source or "auth" in target or "permissions" in " ".join(item["target"] for item in interactions):
        return "CONTROL"
    if "audit" in source or "audit" in target or "notifications" in source or "notifications" in target:
        return "OBSERVABILITY"
    if "dashboard" in source or "dashboard" in target or "settings" in source or "settings" in target:
        return "UI_COMPOSITION"
    if existing and existing.get("type") == "aggregates":
        return "DOMAIN"
    if "writes" in types:
        return "DOMAIN"
    if any(item["target"].startswith("entity.") for item in interactions):
        return "DATA"
    if "calls" in types:
        return "APPLICATION"
    return "APPLICATION"


def infer_importance(dep_id: str, source: str, target: str, classification: str, types: list[str]) -> str:
    if dep_id in MAIN_DEPENDENCY_IDS:
        return "PRIMARY"
    if classification in SUPPORTING_CLASSES:
        return "SUPPORTING"
    if source == "module.participants" and target == "module.memberships":
        return "SECONDARY"
    return "SECONDARY"


def infer_visibility(classification: str, importance: str) -> str:
    if importance == "PRIMARY":
        return "MAIN"
    if classification in SUPPORTING_CLASSES:
        return "DETAIL"
    return "DETAIL"


def infer_confidence(interactions: list[dict[str, Any]], existing: dict[str, Any] | None) -> str:
    if existing and existing.get("confidence") == "high":
        return "high"
    if interactions and all(item.get("confidence") == "high" for item in interactions):
        return "high"
    return "medium"


def apply_override(dependency: dict[str, Any], overrides: dict[str, dict[str, Any]]) -> None:
    override = overrides.get(dependency["id"])
    if not override:
        return
    for key in ["classification", "importance", "default_visibility"]:
        if key in override:
            dependency[key] = override[key]
    dependency["override_applied"] = True


def strongest_type(types: list[str]) -> str:
    priority = ["writes", "aggregates", "calls", "reads", "renders", "observes"]
    for item in priority:
        if item in types:
            return item
    return types[0] if types else "calls"


def risk_for(classification: str, importance: str) -> str:
    if importance == "PRIMARY":
        return "high"
    if classification in SUPPORTING_CLASSES:
        return "low"
    return "medium"


def reason_for(source: str, target: str, classification: str, types: list[str]) -> str:
    return f"{source} depends on {target} through observed {', '.join(types)} interactions classified as {classification}."


def merge_evidence(interactions: list[dict[str, Any]], existing: dict[str, Any] | None) -> list[dict[str, Any]]:
    evidence = []
    if existing:
        evidence.extend(existing.get("evidence", []) or [])
    for item in interactions:
        evidence.extend(item.get("evidence", []) or [])
    seen = set()
    result = []
    for item in evidence:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result


def evidence_from_item(item: dict[str, Any], ref: str) -> list[dict[str, str]]:
    evidence = []
    if item.get("source_file") or item.get("router_file"):
        evidence.append({"file": str(item.get("source_file") or item.get("router_file")), "symbol": str(item.get("source_symbol") or item.get("handler") or item["id"])})
    evidence.append({"source": item["id"], "target": ref})
    return evidence


def find_architectural_cycles(dependencies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relevant = [dep for dep in dependencies if dep["importance"] in {"PRIMARY", "SECONDARY"} and dep["classification"] not in SUPPORTING_CLASSES]
    by_pair = {(dep["from"], dep["to"]): dep for dep in relevant}
    cycles = []
    for dep in relevant:
        reverse = by_pair.get((dep["to"], dep["from"]))
        if not reverse:
            continue
        cycle_id = f"cycle.{slug(min(dep['from'], dep['to']))}.{slug(max(dep['from'], dep['to']))}"
        cycles.append(
            {
                "id": cycle_id,
                "type": "CIRCULAR_DEPENDENCY",
                "modules": sorted([dep["from"], dep["to"]]),
                "dependencies": sorted([dep["id"], reverse["id"]]),
                "severity": "MEDIUM" if dep["importance"] == "SECONDARY" and reverse["importance"] == "SECONDARY" else "HIGH",
            }
        )
    deduped = {item["id"]: item for item in cycles}
    return sorted(deduped.values(), key=lambda item: item["id"])


def build_dependency_metrics(snapshot: dict[str, Any], observed: list[dict[str, Any]], canonical: list[dict[str, Any]], cycles: list[dict[str, Any]]) -> dict[str, Any]:
    connected = {module_id for dep in canonical for module_id in [dep.get("from"), dep.get("to")] if module_id}
    modules = {module["id"] for module in snapshot.get("modules", []) or []}
    expected_isolated = {
        module["id"]
        for module in snapshot.get("modules", []) or []
        if str(module.get("isolation_policy") or "").upper() == "EXPECTED_ISOLATED" or "infrastructure" in module["id"]
    }
    suspicious_isolated = sorted(modules - connected - expected_isolated)
    return {
        "observed_interaction_count": len(observed),
        "canonical_dependency_count": len(canonical),
        "primary_dependency_count": sum(1 for dep in canonical if dep["importance"] == "PRIMARY"),
        "secondary_dependency_count": sum(1 for dep in canonical if dep["importance"] == "SECONDARY"),
        "supporting_dependency_count": sum(1 for dep in canonical if dep["importance"] == "SUPPORTING"),
        "unclassified_candidate_count": sum(1 for dep in canonical if dep.get("confidence") == "low"),
        "suspicious_isolated_count": len(suspicious_isolated),
        "circular_dependency_count": len(cycles),
    }


def slug(value: str) -> str:
    cleaned = []
    for char in value.replace("module.", "").replace("dependency.", "").lower():
        if char.isalnum():
            cleaned.append(char)
        elif cleaned and cleaned[-1] != "_":
            cleaned.append("_")
    return "".join(cleaned).strip("_") or "unknown"


def main() -> dict[str, Any]:
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    apply_dependency_model(snapshot)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    metrics = snapshot["dependency_metrics"]
    print("Dependency model normalized:")
    for key, value in metrics.items():
        print(f"- {key}: {value}")
    return metrics


if __name__ == "__main__":
    main()
