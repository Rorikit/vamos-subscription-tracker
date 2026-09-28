# Model Readiness

Semantic validation and model readiness are separate checks.

Semantic validation answers: is `architecture_snapshot.json` structurally correct and are references valid?

Model readiness answers: is there enough trustworthy architecture data to render a specific model without inventing missing knowledge?

## Readiness statuses

- `READY` - enough data exists for a reliable model projection.
- `PARTIAL` - a model can be shown, but coverage is incomplete or important facts are derived/declared.
- `MISSING` - critical required collections are absent.
- `INVALID` - data exists but violates schema or semantic contracts.

`PARTIAL` and `MISSING` are diagnostic states. They should not fail CI by themselves. Semantic `INVALID` must fail validation/build.

## Coverage

Coverage is model-specific:

- System Map: connected modules over all modules.
- Domain Model: entities participating in relationships.
- Use Case Model: actors, permissions and use case to process coverage.
- Activity Model: business processes linked to use cases and modeled with decisions/rules.
- State Model: modeled stateful entities over potential stateful entities.
- Sequence Model: use cases with canonical interactions.
- Data Model: persistent entities mapped to `DataTable`.
- Component Model: services/API mapped to architecture components.
- Deployment Model: architecture components mapped to deployment nodes.

Default thresholds:

- `READY`: coverage >= 0.8
- `PARTIAL`: coverage > 0
- `MISSING`: coverage == 0 or required data missing

Some models intentionally lower coverage when data is only declared/derived or when owner review is required.

## Suspicious isolated modules

An isolated module is not automatically a problem. It is suspicious only when:

- the module has graph degree 0;
- other modules reference its entities/API/services/routes; or
- observed cross-module interactions suggest a missing dependency edge.

Expected isolated modules are shown separately and do not imply failure.

## Dependency candidates

Dependency candidates are inferred from observed references across module ownership boundaries.

They do not modify `cross_module_dependencies`. They are diagnostics for the architecture owner.

## Traceability coverage

For every UseCase the readiness engine checks:

Actor -> UseCase -> Process -> Interaction -> Service -> API -> Entity -> DataTable

Not every use case must have every layer, but missing links are reported so future diagrams do not pretend full coverage.

## Diagnostic rule ids

- `READINESS-001` - model missing required collection.
- `READINESS-002` - model coverage below ready threshold.
- `MODULE-ISO-001` - isolated module has external references.
- `MODULE-DEP-001` - observed cross-module interaction has no dependency.
- `MODULE-DEP-002` - dependency direction mismatch.
- `STATE-001` - stateful entity has no canonical states.
- `STATE-002` - stateful entity has states but no transitions.
- `STATE-003` - business rule changes state without transition.
- `USECASE-001` - UseCase has no BusinessProcess.
- `USECASE-002` - UseCase has no Interaction.
- `TRACE-001` - traceability chain incomplete.
- `DATA-001` - persistent entity has no DataTable mapping.
- `COMPONENT-001` - service has no architecture component.
- `DEPLOY-001` - architecture component is not deployed.
- `SOT-001` - Source of Truth conflict.
- `SOT-002` - Source of Truth has invalid consumer.

## Determinism

For the same snapshot, `readiness_report` must be identical except snapshot metadata such as generation time. Models, diagnostics, IDs and metrics are sorted deterministically.
