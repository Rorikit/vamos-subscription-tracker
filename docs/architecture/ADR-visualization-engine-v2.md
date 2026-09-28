# ADR: Architecture Diagrams Are Generated Through DiagramSpec Projections

## Status

Accepted.

## Context

Architecture Hub needs multiple visual views: System Map, Domain Model, State, Activity, Sequence, Data, Component and Deployment. Earlier graph code mixed snapshot traversal, semantic projection, layout and rendering in feature-specific React logic.

That made layout regressions harder to diagnose and encouraged duplicated graph engines.

## Decision

All architecture diagrams must use this pipeline:

```text
Snapshot -> ArchitectureIndex -> Projection Compiler -> DiagramSpec -> Validation -> Layout -> Renderer
```

`DiagramSpec` is the canonical intermediate format for visualization. It is independent from ReactFlow and does not store coordinates.

## Consequences

- Stable architecture IDs remain in the model layer.
- Russian labels remain presentation data.
- Layout coordinates live only in `LayoutResult`.
- Renderer consumes `DiagramSpec + LayoutResult`.
- New diagram views should add projection compilers instead of new ad hoc graph engines.
- Layout may choose among deterministic candidates, but it must not invent architecture relationships.
