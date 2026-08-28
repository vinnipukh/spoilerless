# React/Cytoscape topology-aware scene reconciliation

Use this reference when one persistent Cytoscape canvas switches between complete graph scenes, especially compound and flat projections.

## Failure signature

A target payload can be internally valid yet the browser throws while switching views:

```text
Can not create edge `<edge-id>` with nonexistent target `<shared-node-id>`
```

Typical stack:

```text
cytoscape restore -> Core.add -> react-cytoscapejs patch/updateCytoscape
```

Do not assume a dangling backend edge. Validate both payloads first, then reproduce the transition with real Cytoscape and the real adapter.

## Root cause class

`react-cytoscapejs` 2.x computes old-only/new-only/same-ID sets, then removes old-only elements before adding new-only elements and patching shared IDs. Cytoscape removal is topology-aware: removing an obsolete compound parent cascade-removes its children and incident edges.

If a child ID exists in both scenes but its old parent does not, the wrapper still considers the child shared. Parent removal deletes it behind the wrapper's plan. A later edge add then references a target that no longer exists.

Static DTO validation cannot detect this because every endpoint exists in the target payload. The defect is in operation ordering and identity reconciliation.

## Deterministic RED harness

Use real `cytoscape` plus `react-cytoscapejs`, not a mocked React component. Minimal old scene:

- obsolete compound parent
- shared child under that parent

Minimal next scene:

- the shared child as a flat node
- one new node
- one new edge targeting the shared child

Run the same transition repeatedly. Before the fix, every iteration should throw the nonexistent-target error. Also run a repo-specific harness using the real legacy projection and target visualization adapter.

## Safe reconciliation order

For a complete target scene:

1. Snapshot runtime state for shared IDs: object identity, node position, classes, selection. Leave camera pan/zoom untouched.
2. Add incoming-only nodes first, preserving parent-before-child declaration order.
3. Detach or reparent shared nodes before removing stale compound parents.
4. Rewire same-ID edges before removing old-only endpoints.
5. Remove stale edges.
6. Remove stale nodes/parents only after shared descendants are safe.
7. Add incoming-only edges last.
8. Patch non-topology data on shared elements. Treat `id`, `source`, `target`, and `parent` as topology keys; do not mutate them through generic data patching.
9. Restore shared node positions, runtime classes, and selection. Do not call global `fit()` or an unconditional layout.

Wrap operations in `cy.batch()`.

## React integration

Keep the `<CytoscapeComponent>` mounted to preserve camera and selection. Do not use a changing `key` as the normal fix.

Prevent the wrapper's unsafe declarative diff from running after mount:

- Capture initial `elements` and initial `layout` in refs.
- Pass those stable refs to `<CytoscapeComponent>`.
- Reconcile subsequent `elements` imperatively in a parent effect.
- Run the app's guarded layout effect after reconciliation. New nodes may receive local placement; tab switches must not trigger an uncontrolled global relayout.

Effect ordering matters: declare reconciliation before the layout effect so target topology exists before layout decisions run.

### Lightweight test-adapter fallback

Many React tests replace `react-cytoscapejs` with a partial component stub and inspect its `elements`/`layout` props. Always passing the stable initial refs makes those tests observe stale scenes, while calling the real reconciler against a partial `cy` object throws on missing collection APIs.

Use a synchronous capability ref, populated inside the `cy` callback, to select the integration path:

- A real Cytoscape core must expose the collection and mutation surface the reconciler uses (`elements().map`, `nodes`, `edges`, `add`, `remove`, and `batch`). Keep stable initial props and reconcile imperatively.
- A partial test/embedded adapter should receive current declarative `elements` and `layout`, and the reconciliation effect should return without mutating it.

Do **not** call React state setters from the `cy` callback solely to record this capability. Test stubs commonly invoke that callback during their own render, producing `Cannot update a component while rendering a different component` and allowing the first passive effect to run against the unsupported adapter. A mutable ref records the capability synchronously without scheduling a render; later graph/mode renders can read it and use declarative props.

This fallback is for adapter compatibility only. Real scene-transition safety must still be verified by the headless Cytoscape matrix below; passing mocked-component tests does not prove topology correctness.

## Regression matrix

Use real headless Cytoscape tests for:

1. Compound -> flat scene with a shared child and incoming edge.
2. Flat -> compound reverse transition.
3. Same-ID edge whose endpoint changes while the old endpoint is removed.
4. Character/investigation/full projection transitions in both directions.
5. Episode boundary changes.
6. Expansion add -> undo/collapse.

Assert:

- Exact final ID set.
- Every edge endpoint resolves.
- Shared element object identity survives.
- Shared node position survives.
- Runtime classes and selection survive.
- Pan/zoom survive.
- No unexpected global layout.

A mocked Cytoscape component is insufficient; it can verify request wiring but cannot exercise cascade deletion.

## Related visualization contract pitfall

Legacy edges may expose `edgeType`; visualization projections may expose only a human `relationClass`. Styling and selection should use:

```text
edgeType ?? relationClass
```

Map human classes to the same color families without re-exposing raw database relationship names.

## Verification sequence

1. Run focused real-Cytoscape reconciler tests.
2. Run the frontend production build/typecheck.
3. Reload the local app in an isolated browser.
4. Exercise Story <-> Characters <-> Evidence <-> Advanced, episode changes, expansion/undo, and temporary Answer Graph restoration.
5. Confirm no ErrorBoundary and no console exception.
6. Run the full frontend suite and the project-approved isolated backend suite before milestone close.
