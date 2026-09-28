# Architecture Snapshot Metamodel

`architecture_snapshot.json` is the canonical machine-readable architecture model for Vamos Subscription Tracker.

Current versions:

- `schema_version`: 2
- `model_contract_version`: 1

## Canonical object types

- `Module` - functional product area, for example Schedule, Finance, Memberships.
- `Actor` - human/system participant in a scenario.
- `Role` - RBAC role used by access checks.
- `Permission` - explicit capability required by UI/API actions.
- `UseCase` - user-level goal, independent from API shape.
- `BusinessProcess` - ordered domain workflow that may support a use case.
- `Interaction` - message-level flow between components/services/entities.
- `Entity` - domain object from application logic.
- `State` - named lifecycle value owned by one entity.
- `Transition` - allowed state movement caused by a rule or action.
- `BusinessRule` - product invariant or calculation rule.
- `Service` - backend service or cohesive business logic unit.
- `APIEndpoint` - HTTP operation exposed by backend.
- `DataTable` - physical persistence table.
- `Component` - runtime/build component such as frontend, backend, database.
- `DeploymentNode` - environment/container/host where components run.
- `ExternalSystem` - system outside the application boundary.

## Required fact metadata

Every stable architecture object should include:

- `id` - stable identifier, never derived from display order.
- `source_type` - `EXTRACTED`, `DERIVED`, or `DECLARED`.
- `confidence` - `high`, `medium`, or `low`.
- `evidence` - compact links to code, route, table, file, or inference reason.

## Relation type registry

All relation `type` values must be present in `relation_type_registry`. Wildcard references such as `api.*` are not allowed in semantic relations.

Core relation groups:

- ownership: `owns`, `contains`, `persisted_as`, `deployed_on`
- dependency: `depends_on`, `calls`, `reads`, `writes`, `renders`, `requires`
- process: `starts`, `continues`, `finishes`, `triggers`, `compensates`
- state: `transitions_to`
- control: `allowed_for`, `permission_for`, `source_of_truth`
- financial: `aggregates`, `calculates`, `pays_out`

## Separation rules

- Actor is not Role. Actor describes who performs work; Role describes access control.
- UseCase is not API. One use case may require many routes and API endpoints.
- BusinessProcess is not a diagram. Diagrams are generated views over process data.
- Entity is not DataTable. Entity captures domain meaning; DataTable captures persistence.
- State belongs to exactly one Entity.
- Interaction participants must be existing architecture IDs.
