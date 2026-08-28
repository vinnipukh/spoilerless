# Persistent Cytoscape scene reconciliation (2026-08-14)

Use when a tab/view/data switch updates one mounted `react-cytoscapejs`
instance and Cytoscape reports a missing endpoint even though both payloads
are statically closed.

## Proven failure mode

The Story scene is built by `graphToElements()` with synthetic compound
parents (`cluster:Ep #N`); neutral visualization DTOs use only editorial DTO
`groups` and may therefore be flat. `react-cytoscapejs@2.0.0` reconciles by
ID in this order:

1. collect old-only IDs and call `cy.remove()`;
2. `cy.add()` new-only definitions;
3. patch same-ID elements with `cyEle.json()`.

Cytoscape removal is topology-aware even though the wrapper diff is not:
removing a compound parent recursively removes descendants and incident edges.
A child ID classified as shared by the prop diff can therefore disappear from
the actual core. It is not in `toAdd`, and later same-ID patches target an
empty handle. A new edge referencing that child then throws, or a transition
can return without throwing while silently losing elements.

Validated live Dexter S01E01 numbers:

- legacy response: 113 nodes / 163 edges;
- rendered Story Overview: 1 parent / 24 child nodes / 34 edges (59 total);
- Character Network DTO: 0 parents / 30 nodes / 28 edges (58 total);
- ID diff: 27 shared, 32 old-only, 31 new-only;
- requested old-only removal: 32; actual recursive removal: all 59;
- both element arrays had zero static dangling edges; a fresh headless core
  accepted the Character scene;
- sequential Story -> Characters failed 20/20 with the production error.

The reported edge existed in both *raw* API payloads but was absent from the
rendered legacy Overview, so it was new-only. Camilla was new-only and got
re-added; Dexter was shared by ID but had been recursively removed with its
old compound parent. This is frontend patch order/identity, not backend
closure.

Relevant seams (line numbers at diagnosis):

- `frontend/src/App.tsx:269-310,854-871` — active projection fetch/wiring;
- `frontend/src/components/graph/graphElements.ts:38-42,77-137` — legacy
  Overview + synthetic parents;
- `frontend/src/lib/visualizationAdapter.ts:77-133` — DTO groups/nodes/edges;
- `frontend/src/components/graph/GraphCanvas.tsx:482-508,860-994` — swaps
  element arrays on one mounted wrapper;
- `node_modules/react-cytoscapejs/src/patch.js:84-135` — remove/add/patch;
- `node_modules/cytoscape/src/collection/index.mjs:592-634` — recursive
  descendant/incident-edge removal.

## Tight headless RED probe

Run from `frontend/`; no browser or files are needed:

```bash
node --input-type=module -e 'import cytoscape from "cytoscape";import RC from "react-cytoscapejs";const t="dexter:character:dexter_morgan",s="dexter:character:camilla_figg",e="dexter:claim:s01e01:camilla_works_dexter:edge",old=[{data:{id:"cluster:Ep #1",isCluster:true}},{data:{id:t,parent:"cluster:Ep #1"}}],next=[{data:{id:t}},{data:{id:s}},{data:{id:e,source:s,target:t}}],base={...RC.defaultProps,headless:true,styleEnabled:false,layout:null,stylesheet:[]};let n=0,msg="";for(let i=0;i<20;i++){const cy=cytoscape({headless:true}),c=new RC({});c._cy=cy;try{c.updateCytoscape(null,{...base,elements:old});c.updateCytoscape({...base,elements:old},{...base,elements:next})}catch(x){n++;msg=x.message}cy.destroy()}console.log(`failures=${n}/20\n${msg}`);if(n!==20)process.exit(1)'
```

Expected current-code signal: `failures=20/20` plus nonexistent Dexter target.

## Diagnosis sequence

Use this differential before touching backend projection code:

1. Check unique IDs and endpoint/reference closure in each payload.
2. Build both adapter element arrays and check closure again.
3. Initialize a fresh headless core with the destination; expect success.
4. Apply source then destination through the real wrapper update path.
5. Compare the final core ID set to the destination ID set even if no exception
   was thrown. `not.toThrow()` alone misses silent loss.
6. Inspect requested removals versus the collection actually returned by
   `cy.remove()`; unexpected shared IDs prove cascade invalidated the diff.

## Safe remediation shape

Preferred: own or patch a topology-aware reconciler while keeping the instance
mounted. In one batch:

1. add incoming-only parents/nodes;
2. reparent shared nodes and rewire changed shared edges while required nodes
   exist;
3. remove old-only edges, nodes, then parents;
4. add incoming-only edges;
5. patch remaining data/classes/positions.

A two-commit bridge that detaches shared children before deleting old parents
can fix the current compound-to-flat case, but must handle rapid switches,
group-to-group moves, and same-ID edges whose endpoints change. Flattening all
parent topology is mechanically simple but changes episode-band/editorial-group
semantics. Do not catch the exception, filter the valid edge, use an
ErrorBoundary as the fix, or key/remount Cytoscape: those mask the cause and
break stable camera/selection/layout identity.

## Regression requirements

A prop-only Cytoscape mock is not enough. Add a headless real-library seam and
assert:

- Story -> Characters and reverse;
- Characters <-> Evidence; Evidence <-> Advanced; temporary Answer Graph;
- Episode 1 <-> Episode 2 in every scene family;
- expansion/add -> undo/collapse, including overlapping additions;
- exact final ID set and edge endpoints, not only no exception;
- shared object identity, position, classes/selection, zoom/pan;
- no uncontrolled global layout during view switches.

The existing App test only asserted the visualization request URL, and its
mock simply rendered the latest props. That proved wiring but could not model
recursive removal. Keep that test, but pair it with a stateful real-engine
transition test.

## Adjacent blockers found

- `GraphCanvas` changes the declarative layout prop by view, so
  `react-cytoscapejs` runs `patchLayout`; its own effect may run another layout.
  A successful tab transition can therefore perform an uncontrolled global
  relayout. Stabilize/suppress the declarative layout path and use stored
  presets/local placement per the scene contract.
- `visualizationAdapter` emits `relationClass`, while graph edge styling and
  edge-tap selection read `edgeType`. Align the data contract and pin it with
  an adapter + interaction test.
- Checked-in synthetic legacy episode fixtures reuse some edge IDs for
  different endpoints. Episode 2 -> 1 returned without throwing but silently
  lost those edges under the naive patch. Either correct fixture identity or
  ensure the reconciler safely handles endpoint moves; always assert final
  endpoints.

Direct live Character clues expansion/undo was patch-safe in the isolated
headless seam (20/20 pass, 58 -> 70 -> 58, camera/selection class retained),
but still needs a GraphCanvas-level no-global-layout regression.
