# Model Contract: Activity Model

Purpose: generate activity diagrams from real business processes.

Required snapshot sections:

- `business_processes`
- `use_cases`
- `business_rules`

Required fields:

- BusinessProcess: `id`, `name_ru`, `use_case`, `steps`
- Step: `order`, `action`, `ref`

Validation:

- process steps must be ordered;
- each `ref` must be either empty or a concrete architecture ID;
- a process should link to a use case where possible.
