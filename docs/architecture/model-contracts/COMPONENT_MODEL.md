# Model Contract: Component Model

Purpose: show runtime/build components and contained responsibilities.

Required snapshot sections:

- `components`
- `services`
- `api`
- `frontend_routes`
- `data_tables`

Required fields:

- Component: `id`, `name_ru`, `kind`, `contains_services`, `contains_routes`, `requires_api`, `exposes_api`, `contains_tables`

Validation:

- contained services/routes/API/tables must exist;
- frontend depends on API, not on database tables directly;
- database contains tables, not domain entities.
