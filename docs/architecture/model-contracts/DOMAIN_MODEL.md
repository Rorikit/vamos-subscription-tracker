# Model Contract: Domain Model

Purpose: render domain entities, their business relationships and role in the product domain.

Domain Model is a projection of `architecture_snapshot.json`, not a separate model and not an ER diagram.

Required snapshot sections:

- `entities`
- `relationships`
- `business_rules`
- `modules`
- `sources_of_truth`
- `stateful_entities`
- `states`
- `transitions`

Required fields:

- Entity: `id`, `name_ru`, `module`, `description`, `relationships`
- Relationship: `id`, `from`, `to`, `type`, `cardinality`

Validation:

- every relationship endpoint must be an existing entity;
- every entity module must exist;
- business rules may reference entities but must not redefine persistence.
- SQL tables, columns, API and services are detail-panel evidence, not graph nodes.
- Persistence-backed relationships must be marked as such when they are inferred from ORM/DB foreign keys.
- Legacy/deprecated entities must remain visible but muted.
