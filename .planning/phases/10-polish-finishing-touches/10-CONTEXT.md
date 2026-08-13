# Phase 10: Polish & Finishing Touches + Narrative Visualization Redesign - Context

**Gathered:** 2026-08-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 10 expands beyond its original closeout-only boundary. User explicitly chose to combine original `POLISH-01..03` regression/UAT/docs closeout with a major Spoilerless narrative-visualization redesign.

Deliver reduced, task-specific visual projections over the existing spoiler-safe storage and GraphRAG graphs; coordinated story, character, evidence, neighborhood, timeline, Answer Graph, and advanced views; semantic expansion; stable scene state; neutral visualization DTOs; benchmarks; real S01E01/S01E02 comparison. Keep Cytoscape.js. Preserve complete Neo4j and GraphRAG detail. Backend spoiler filtering remains before projection.

No unrelated authentication, settings, chat, Notes, ChangeSet, ingestion, renderer, or ontology redesign. Existing functionality must remain working.

</domain>

<decisions>
## Implementation Decisions

### Scope amendment
- **D-01:** Phase 10 includes both original polish obligations and narrative visualization redesign. This supersedes ROADMAP's prior “no new features or architectural changes” sentence. Planner must reconcile `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` before execution.
- **D-02:** Work incrementally: audit/baseline; neutral DTO; Episode Overview projection; Cytoscape adaptation; stable layout; timeline sync; expansion; Answer Graph/Evidence Chain; benchmark/refine; final regression/UAT/docs.
- **D-03:** Significant architecture choices require concise evidence-based Decision Log: observed problem, alternatives, repository evidence, choice, reason, rejection, remaining risk.

### Graph separation and spoiler boundary
- **D-04:** Storage graph, GraphRAG retrieval graph, visual projection are separate systems. Visual reduction never deletes Neo4j detail or limits GraphRAG safe knowledge.
- **D-05:** Mandatory order: Neo4j, spoiler filtering, visualization projection, serialization, frontend. `effective_view_order = min(requested_view_order, watched_progress)` applies to graph, expansion, path, search, autocomplete, GraphRAG focus, saved restoration.
- **D-06:** Audit indirect leaks: hidden counts/degrees/layout forces/space/group names/expansion hints/search ranking/path existence/focus IDs/cache/totals. Future elements must not influence visible projection or layout. Importance uses safe-boundary editorial data, never full-graph degree.

### Renderer and visual projections
- **D-07:** Keep Cytoscape.js. NVL may exist only as isolated `/viz-lab` experiment; never production dependency.
- **D-08:** Backend returns library-neutral visualization DTO (`metadata`, `nodes`, `edges`, `groups`, `timeline`, `focus`). Frontend owns `toCytoscapeElements()` and timeline adapters.
- **D-09:** Default Episode Overview target 12–28 nodes, hard max 40; preferred under 35 edges, hard max 60; persistent procedural labels 0.
- **D-10:** Evaluate two fixed-data Episode Overview variants before choosing: A characters + major Events; B mostly Character Network, Events primarily timeline. Compare counts, crossings, clarity, stability, episode comprehension.
- **D-11:** Full Graph remains Advanced/debug/deep exploration, never default.

### Event and relationship presentation
- **D-12:** Detailed Events remain canonical and GraphRAG-accessible. Main visualization uses major/supporting/micro distinction, reusing existing cluster/sequence/plot metadata where possible.
- **D-13:** Episode Overview omits `PARTICIPATED_IN` and `OCCURRED_IN`. Participation becomes avatars/chips/highlighting/Inspector/timeline lists. Episode membership becomes context metadata. `LOCATED_IN` usually becomes Event-card metadata.
- **D-14:** Classify edges as narrative versus procedural. Raw Neo4j relation names stay hidden outside explicit debug mode. Label policy supports `never`, `on_hover`, `on_select`, `on_path`, `medium_zoom`, `always`; human wording replaces technical names.
- **D-15:** Canonical visual importance field is `display_tier` unless audit proves an equivalent exists. Semantics: 1 core, 2 supporting, 3 detail; classification valid only at resource's visible boundary.

### View navigation and mobile structure
- **D-16:** Desktop uses top-level tabs.
- **D-17:** Four top-level tabs: **Story**, **Characters**, **Evidence**, **Advanced**. Specialized modes nest contextually rather than exposing seven equal tabs.
  - Story: Episode Overview + Event Timeline coordination.
  - Characters: Character Network + Local Neighborhood.
  - Evidence: Investigation/Evidence Chain + temporary GraphRAG Answer Graph.
  - Advanced: Full Graph Explorer/debug tools.
- **D-18:** Mobile mirrors same hierarchy using horizontally scrollable top tabs, not bottom navigation.
- **D-19:** Mobile Inspector opens as bottom sheet with half-height and full-height states, preserving graph/timeline context.
- **D-20:** Do not squeeze graph, timeline, Inspector simultaneously onto narrow screens.

### Interaction and scene state
- **D-21:** Semantic expansion keys are human concepts (`family`, `work`, `conflict`, `episode_events`, `clues`, `locations`, `evidence`), server allowlisted and spoiler-safe. Preferred 8–12 additions, hard max 25. No hidden totals or future hints. Collapse, Undo, Reset required.
- **D-22:** Expansion preserves scene: existing important nodes fixed/constrained; new nodes arranged locally via concentric/local fCoSE. Never rerun random global layout.
- **D-23:** Initial Overview/Character layout uses fCoSE, then stored preset positions. Shared characters remain mostly stable across Episode changes. Evidence uses ELK/Dagre; timeline uses React/CSS.
- **D-24:** Stable Cytoscape instance. React state owns scene; Cytoscape changes apply through batched diffs. Selection dims unrelated content, syncs Inspector/timeline, preserves camera, never triggers relayout.
- **D-25:** Semantic zoom changes labels/icons/secondary text only. Zoom never fetches or expands graph data.

### GraphRAG and evidence
- **D-26:** GraphRAG keeps full spoiler-safe retrieval graph. Visible focus highlights in place; hidden safe focus opens small temporary Answer Graph; micro Event maps to visible major Event plus Inspector detail; Claim/Evidence opens Evidence Chain.
- **D-27:** Answer Graph target 5–20 visual elements. Closing restores camera, selection, expansions, timeline state.
- **D-28:** Investigation view answers “Why do we know this?” using layered Claim/Evidence/Source path; never placed on default Episode Overview.

### Backend, cache, tests, closeout
- **D-29:** Task-specific graph endpoint supports `episode_overview`, `character_network`, `plot_threads`, `investigation`, `full`, `graphrag_focus`; expansion endpoint enforces boundary, allowlist, limit server-side. Reuse repository architecture; do not create every conceivable endpoint merely because it appears in design notes.
- **D-30:** Projection cache key includes series, effective order, view type, projection version, graph revision, user scope where needed. Never cross-return view or boundary. Prefer existing revision invalidation over cache redesign.
- **D-31:** Baseline fixed safe snapshots for S01E01 and cumulative S01E02. Measure current Character/Event/Location/Object/Organization counts, total nodes/edges, `PARTICIPATED_IN`, `OCCURRED_IN`, direct Character relations, initial layout duration, response latency, payload size before production behavior changes.
- **D-32:** Benchmarks cover 30/50, 75/150, 150/400, 300/1000 node/edge datasets; optional 1000-node stress case only if cheap. Measure enough to find product regressions: payload/latency, adapter, init/layout, interaction, expansion, switch, memory, React commits, displacement, labels/crossings. Avoid academic harness work.
- **D-33:** Automated tests cover spoiler-before-projection, fail-closed missing visibility, publication/reveal-order security, bounds, Episode 1 safety, expansion, hidden leaks, GraphRAG independence/focus, cache separation, deterministic IDs, default view, timeline sync, label hiding, focus, collapse/reset, stable positions, Episode switch, Answer Graph, Evidence Chain, Inspector, search/filter preservation, Chat focus, responsive UI.
- **D-34:** Finish original Phase 10 obligations: backend pytest, spoiler/projection/GraphRAG/ChangeSet tests; frontend vitest/lint/typecheck/build; `git diff --check`; real golden-path UAT; shipped-state README/root docs. Tests make no production LLM calls. Manual tasks include login, Dexter family, Doakes distrust, Episode events/clues/cases, Notes/export, return to Overview, GraphRAG visualization, expansion/collapse, refresh, Episode 2 to 1 spoiler disappearance.

### Narrative semantics and timeline security
- **D-35:** Reveal/publication order is authoritative for spoiler security. Fictional chronology may be optional display metadata only; flashbacks remain gated by first reveal Episode.
- **D-36:** Plot threads are editorial story concepts, never automatic graph communities. Group labels, membership, collapsed metadata, and counts must all be spoiler-safe. No future member totals.
- **D-37:** Visual aggregation may summarize safe micro Events through an existing major/parent Event; it must not invent canonical Character relationships or mutate ontology semantics.
- **D-38:** Event timeline is first-class React/CSS UI grouped by spoiler-safe plot thread. Event cards expose participants and Location as metadata. Graph/timeline selection is bidirectional; graph focus remains optional and camera-preserving.
- **D-39:** `episode_difference` (“What changed in this Episode?”) is valuable but secondary. Plan only after Episode Overview is stable; defer if it threatens highest-priority deliverable.

### Product polish, resilience, and accessibility
- **D-40:** Phase is primarily product/frontend polish plus projection architecture, not major backend rewrite. Backend work stays limited to neutral DTOs, spoiler-safe projections/expansion/focus, cache separation, and required tests.
- **D-41:** Claims, EvidenceFragments, and Sources stay off main story graph. Inspector tabs remain Overview, Claims, Evidence, Sources, Notes where current permissions allow. Opening citation prefers evidence detail; main graph changes only on explicit “Show in graph.”
- **D-42:** Origin styling stays restrained: canonical normal; candidate small draft/warning marker; user small pencil badge or subtle dashed border. Do not create a color-heavy provenance taxonomy.
- **D-43:** Character images must be Episode-safe. Unknown identities use neutral visuals; invalid/missing images fall back to initials, silhouette, or icon. Images cannot reveal future costume, injury, age, relationship, or identity.
- **D-44:** Loading transitions keep prior scene visible where practical, avoid graph flashing, incrementally update shared elements, and do not recreate Cytoscape on Episode change. Projection/layout/image/Inspector/expansion failures show graceful retry states without internal Neo4j errors. Sparse Episodes show explanatory empty state.
- **D-45:** Accessibility must not regress: keyboard-focusable controls, visible focus, accessible Inspector/search or readable node access, non-color distinctions, reduced-motion support. No full certification scope.
- **D-46:** General polish audits shared header/actions, graph controls, Episode selector, Filters, Chat/Settings transitions, spacing, typography, radii, icon sizes, panels, hover/active/disabled/focus states. Reuse existing Tailwind design language; no brand redesign and no DaisyUI.
- **D-47:** Views and Filters stay separate. View answers user task; Filters restrict entity types. View changes preserve filters unless an incompatibility requires a documented reset.
- **D-48:** Search remains spoiler-safe. Hidden-safe resources open a local safe projection when absent from current view; search never defaults to Full Graph. GraphRAG focus must narrow broad retrieval context to intentional explanation elements.
- **D-49:** Exploration recovery provides Back, Undo Expansion, Collapse, Clear Focus, Reset to Episode Overview. Browser-history integration and persisted Saved Views remain optional/deferred unless already cleanly supported.

### Claude's Discretion
- Exact nesting controls inside four top-level tabs.
- Exact fCoSE/preset/local-layout tuning and position persistence format.
- Exact DTO field names where repository already has cleaner equivalents.
- Exact benchmark harness and edge-crossing approximation.
- Exact editorial assignment mechanism after auditing existing metadata; do not add parallel priority fields.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase and product scope
- `.planning/ROADMAP.md` §Phase 10 — original POLISH obligations; boundary superseded by D-01.
- `.planning/REQUIREMENTS.md` — `POLISH-01..03`, spoiler and stack constraints; must gain visualization requirements during planning.
- `.planning/PROJECT.md` — core value, spoiler-security invariants, current architecture.
- `.planning/STATE.md` — current milestone position and carried operational context.
- `.planning/phases/09-feature-expansion-full-audit-remediation/09-CONTEXT.md` — prior fCoSE, filter, focus, timeline, test-isolation, GraphRAG, and rebrand decisions.

### Existing architecture and behavior
- `docs/PROJECT-SPEC.md` — product invariants and visual language.
- `docs/ARCHITECTURE.md` — live system boundaries; update after redesign.
- `docs/API.md` — current API contract; update for projections/expansion.
- `docs/PROBLEMS.md` — canonical evidence ledger and graph-density history.
- `frontend/src/components/graph/GraphCanvas.tsx` — stable Cytoscape lifecycle integration point.
- `frontend/src/components/graph/graphElements.ts` — current response-to-Cytoscape assembly.
- `frontend/src/components/graph/layoutConfig.ts` — current fCoSE configuration.
- `frontend/src/components/graph/graphStylesheet.ts` — current semantic styling and label culling.
- `frontend/src/components/graph/GraphFilterPanel.tsx` — existing filters.
- `frontend/src/components/graph/focusReducer.ts` — existing neighborhood focus behavior.
- `frontend/src/components/timeline/TimelineView.tsx` — existing timeline base.
- `frontend/src/components/detail/DetailPanel.tsx` — Inspector base.
- `frontend/src/App.tsx` — current cross-view selection/state coordination.
- `frontend/src/types/graph.ts` and `spoilerless/app/domain/graph.py` — existing frontend/backend graph contracts.
- `spoilerless/app/api/graph.py` — current boundary resolution, graph/path/export API.
- `spoilerless/app/services/graph.py` — current graph assembly/projection candidate.
- `spoilerless/app/cache/graph_cache.py` — existing spoiler-safe graph cache.
- `spoilerless/app/spoiler/policy.py` — effective boundary rule.
- User-provided “Phase 10 Context: Polishing and Graph Visualization Improvements” (2026-08-13) — complete product, spoiler, visualization, polish, performance, acceptance, non-goal, and Definition-of-Done brief; decisions D-35..D-49 capture additions not already explicit in repository files.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Existing Cytoscape/fCoSE stack, compound elements, layout config, filters, focus reducer, zoom culling, search, path highlighting.
- Existing `TimelineView`, `DetailPanel`, GraphRAG citation/focus plumbing, share snapshot, graph cache.
- Existing overview tiers and relationship styles may already provide partial `display_tier`/semantic-edge equivalents; audit before adding fields.

### Established Patterns
- Backend FastAPI/Pydantic/Neo4j repository-service-API layering; backend is spoiler boundary.
- React 19 + Tailwind + stable Cytoscape callback lifecycle. `NODE_ENV=test CI=1` required for vitest.
- Shared live Neo4j tests require scratch series and teardown; never mutate real dev user or `series_dexter`.

### Integration Points
- Backend neutral DTO and projections integrate near domain graph models, graph service, graph API, spoiler policy, cache.
- Frontend adapters sit between graph API types and Cytoscape/timeline.
- Four-view hierarchy and scene reducer integrate in `App.tsx`; Inspector/timeline/GraphRAG selection become shared scene actions.

</code_context>

<specifics>
## Specific Ideas

- Product should feel like interactive story map, not graph-database dump.
- User must understand who matters, what happened/changed, plot threads, clues, evidence without knowing Neo4j terminology.
- Primary labels: Story, Characters, Evidence, Advanced.
- Mobile preserves hierarchy through scrollable top tabs; Inspector uses half/full bottom sheet.
- Success judged by narrative comprehension, not prettier styling.

</specifics>

<deferred>
## Deferred Ideas

- NVL production migration.
- 3D visualization.
- Research-grade StoryFlow optimization.
- Free-form graph editing in Episode Overview.
- Saved scenes beyond state needed for restoration, unless required by current acceptance.
- Unrelated auth/settings/chat/header redesign.

</deferred>

---

*Phase: 10-Polish & Finishing Touches + Narrative Visualization Redesign*
*Context gathered: 2026-08-13*
