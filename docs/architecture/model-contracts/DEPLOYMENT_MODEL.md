# Model Contract: Deployment Model

Purpose: render deployment topology for production and staging.

Required snapshot sections:

- `deployment_nodes`
- `component_deployments`
- `components`

Required fields:

- DeploymentNode: `id`, `name_ru`, `kind`, `description`
- ComponentDeployment: `id`, `from`, `to`, `type`

Validation:

- every deployed component must exist;
- every target deployment node must exist;
- data volume must be modeled as a deployment node when persistence survives container rebuild.
