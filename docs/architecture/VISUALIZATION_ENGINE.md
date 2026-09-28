# Architecture Visualization Engine V2

Architecture Hub renders diagrams through a single projection pipeline:

```text
architecture_snapshot.json
  -> ArchitectureIndex
  -> Projection Compiler
  -> DiagramSpec
  -> DiagramSpec Validation
  -> Layout Engine
  -> Layout Quality Evaluation
  -> Renderer
  -> Architecture Hub
```

## Responsibilities

Snapshot answers: what is known about the architecture.

ArchitectureIndex answers: how to find architecture objects and reverse references efficiently.

Projection answers: which architecture objects belong to a concrete diagram.

DiagramSpec answers: what should be visualized. It is renderer-agnostic and does not contain React components or coordinates.

Validation answers: whether a DiagramSpec can be safely passed to layout.

Layout answers: where nodes and routes should be placed. Coordinates live only in `LayoutResult`.

Quality evaluation answers: whether the chosen layout is usable enough to render.

Renderer answers: how the already projected and laid-out diagram should be displayed.

Inspector answers: what canonical architecture object is behind the selected visual item.

## DiagramSpec

`DiagramSpec` contains:

- `id`, `kind`, `title`
- `nodes`, `edges`
- optional `groups` and `lanes`
- `metadata.sourceArchitectureIds`
- readiness and coverage metadata
- projection version
- layout hints

Nodes have stable diagram IDs, optional `architectureRef`, display labels, badges, metadata and layout hints. Edges have stable IDs, endpoints, type, labels, architecture refs and layout hints.

## Validation

Before layout, the validator checks:

- duplicate node and edge IDs
- dangling edge endpoints
- dangling group and lane refs
- unknown architecture refs when an index is supplied
- required minimum data for diagram kind

Broken specs must not be passed silently to layout.

## Layout

`layoutDiagram(spec, options)` selects candidate layouts for the requested profile:

- `SYSTEM_MAP`
- `DOMAIN`
- `STATE`
- `ACTIVITY`
- `SEQUENCE`
- `ER`
- `USE_CASE`

For graph views it can compare right-layered, down-layered and clustered candidates. The selected layout is deterministic for identical inputs.

V2.1 makes node size a single source of truth: projection supplies deterministic `layoutHints.width/height`, layout uses the same dimensions, and renderer applies fixed `width/height` instead of allowing DOM content to expand cards. Graph cards show topology-level content only; detailed object facts stay in the inspector.

## Quality

The layout engine calculates:

- `nodeOverlapCount`
- `clearanceViolationCount`
- `severeNodeClearanceViolationCount`
- `edgeNodeIntersectionCount`
- `criticalEdgeNodeIntersectionCount`
- `edgeOverlapCount`
- `sharedEdgeSegmentLength`
- `estimatedCrossings`
- `totalEdgeLength`
- `averageEdgeLength`
- `maxEdgeLength`
- `bendCount`
- `backtrackingCount`
- `boundingWidth`
- `boundingHeight`
- `viewportUtilization`
- `aspectRatioDifference`
- deterministic `score`

Hard fail conditions:

- `nodeOverlapCount > 0`
- `severeNodeClearanceViolationCount > 0`
- `criticalEdgeNodeIntersectionCount > 0`

Soft penalties are applied to normal clearance violations, edge overlap, crossings, long edges, backtracking, total edge length, bends and viewport mismatch. Candidate selection ranks hard-fail layouts behind valid candidates before comparing score.

Quality statuses:

- `GOOD`
- `ACCEPTABLE`
- `POOR`
- `INVALID`

`INVALID` layouts should show a fallback/error state instead of rendering a broken diagram.

## Renderer

`GraphRenderer` receives `DiagramSpec + LayoutResult`. It does not know about business entities such as Membership, Finance, Teacher or Schedule. Model-specific presentation is selected from `DiagramNode.type` and metadata prepared by the projection.

The renderer preserves `LayoutResult.edges.sections`, `sourcePort` and `targetPort` in the rendered graph. Edge labels and cardinality labels are positioned against final routed sections, not against independently recalculated paths.

Renderer families prepared by contract:

- GraphRenderer
- StateMachineRenderer
- ActivityRenderer
- SequenceRenderer
- ERRenderer
- UseCaseRenderer

GraphRenderer is production-ready in this stage. Other families are contract-ready for future projections.

## Debug

Add `?diagramDebug=1` to System Map or Domain Model pages to inspect:

- raw architecture refs
- DiagramSpec
- LayoutResult
- selected profile and candidate
- layout quality metrics
- rejected candidate diagnostics
- clearance and edge-overlap metrics

This helps identify whether a visual problem came from data, projection, layout or rendering.

## Decision

Architecture diagrams are generated through DiagramSpec projections.

- Snapshot does not contain UI coordinates.
- Projection does not perform layout.
- Layout does not change architecture semantics.
- Renderer does not read raw snapshot objects directly.
- Visualization engine is a consumer of the architecture model.
