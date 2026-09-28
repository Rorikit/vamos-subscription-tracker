# Model Contract: Sequence Model

Purpose: generate sequence diagrams from interactions.

Required snapshot sections:

- `interactions`
- `business_processes`
- `components`
- `services`
- `api`
- `entities`

Required fields:

- Interaction: `id`, `use_case`, `process`, `participants`, `messages`
- Message: `order`, `from`, `to`, `action`, `ref`

Validation:

- every participant must be an existing architecture ID;
- message endpoints must be existing participants or architecture nodes;
- messages must stay ordered and traceable to a process.
