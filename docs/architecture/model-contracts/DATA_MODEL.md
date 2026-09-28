# Model Contract: Data Model

Purpose: describe physical storage separately from the domain model.

Required snapshot sections:

- `entities`
- `data_tables`
- `entity_table_mappings`

Required fields:

- DataTable: `id`, `name`, `entity`, `columns`
- Mapping: `id`, `from`, `to`, `type`

Validation:

- table references one owning entity;
- mapping type must be `persisted_as`;
- physical columns may mirror entity fields, but should not replace domain meaning.
