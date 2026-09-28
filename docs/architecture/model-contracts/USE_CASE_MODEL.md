# Model Contract: Use Case Model

Purpose: show product goals, actors and required permissions.

Required snapshot sections:

- `actors`
- `roles`
- `permissions`
- `use_cases`

Required fields:

- Actor: `id`, `name_ru`, `represented_by_role`
- UseCase: `id`, `name_ru`, `actors`, `required_permissions`, `entry_points`, `api`, `services`

Validation:

- use cases reference actors, not roles;
- permissions must exist;
- entry points and API references must be concrete IDs.
