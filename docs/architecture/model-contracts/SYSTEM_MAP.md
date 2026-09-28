# Model Contract: System Map

Purpose: render a high-level map of product modules and cross-module dependencies.

Required snapshot sections:

- `modules`
- `cross_module_dependencies`
- `relation_type_registry`

Required fields:

- Module: `id`, `name_ru`, `description`, `entities`, `services`, `api`
- Dependency: `id`, `from`, `to`, `type`, `interaction_types`, `classification`, `importance`, `default_visibility`, `reason`, `evidence`, `observed_interactions`, `via_services`, `via_entities`, `source_type`, `confidence`
- Default System Map renders `PRIMARY` dependencies with `MAIN` visibility.
- `observed_interactions` are raw code-level signals and must not be treated as canonical architecture edges.

Validation:

- every `from` and `to` must reference an existing module;
- relation types must be registered;
- isolated modules must be shown separately, not hidden.
