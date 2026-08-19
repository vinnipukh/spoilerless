# Phase 10 execution + visualization wiring lessons (2026-08-13/14)

## Executor tool-cap resume protocol (recurring: hit on 10-03, 10-05, 10-06, 10-07, 10-08, 10-09, 10-11)

- Every plan executor died at the ~50 tool-call cap mid-plan, usually AFTER writing code but BEFORE verifying/committing. Do not re-dispatch a fresh full-plan executor — resume inline as orchestrator.
- Resume sequence: (1) read `C:/Users/arhan/AppData/Local/hermes/cache/delegation/subagent-summary-0-*.txt` (the pinned handoff — read the middle via offset, head/tail truncate it); (2) `git status --short` to confirm the working tree matches the handoff; (3) finish the remaining verifies/commits inline; (4) never trust "self-report" — re-run the verify commands yourself.
- Tell executors up front: "~50 tool-call budget. COMMIT EARLY: Task 1 verify + commit, then Task 2." Long commands (full test suites, container runs) must go through `background=true` + `notify_on_complete` so they don't eat iterations.
- A subagent write to `.hermes/environment.json` gets blocked (protected file, approval timeout). Tell executors NOT to touch it; the project's own verify chain (vitest + build / focused pytest) is the sanctioned evidence.

## pytest `-k` filter hazard (hang, not failure)

- Broad keywords like `boundary`, `variant`, `restore` match live-DB tests in `test_graph_api.py` (per-test reseed → ~43 min, looks hung, timeout kills). Two 120s timeouts burned before identifying this.
- Safe Phase-10 filter that passes in ~30s: `-k "visualization or projection or cache or exact_operations or locked_inventory"` over the focused files. Run the offline suites (projection/policy/baseline) unfiltered instead of adding terms.

## Visualization DTO wiring decisions (audit-gap closure 260814-viz)

- **Legacy `GraphResponse` stays the scene backbone.** Projection DTOs never contain user content (custom nodes, user-created edges, notes) — wiring Story/Advanced tabs to DTOs broke legacy user-content tests AND UX. Map: Story → legacy scene, Advanced → legacy full graph, Characters → `character_network`, Evidence → `investigation`/`graphrag_focus` (Answer Graph). Spoiler safety identical either way (backend-side filtering).
- **GraphCanvas `visualization` prop semantics**: `undefined` = force legacy (clear the last-DTO ref), `null` = retain last DTO while loading (D-44 no-flash), DTO = render projection. Passing `null` on legacy tabs keeps the DTO pinned forever (lastVisualizationRef) — that's the trap.
- **Expansion merge is App-side**: backend returns a delta DTO; merge into base (dedupe by id over nodes/edges/timeline) before passing to GraphCanvas; GraphCanvas has no expansions prop. Keep records `{anchorId, key, additionIds, dto}` for Undo (pop last) / Collapse (filter by anchor).
- App.tsx uses inline SVGs only (no lucide-react import) — new icons must be inline SVG to match.

## Integration seam audit (how the gap was caught)

- A milestone audit found `fetchVisualization`/`fetchExpansion` defined but **zero callers** while UAT rows claimed the features worked. Grep callers before claiming wiring: `grep -rn "fetchVisualization\|fetchExpansion" frontend/src --include=*.ts --include=*.tsx | grep -v "\.test\." | grep -v "export async"`. UAT-approved rows that describe unwired surfaces are a real blocker-class audit finding — present transparently with the caller-count evidence and let the user choose wire/defer/strip.

## Backend/frontend test quirks hit this session

- `GraphClaim` lacks `episode_id`/`image_url`/`image_source_url` (GraphNode/Source/Evidence have them) — `_node()` must use `getattr(node, attr, None)`; projections mixing node kinds need isinstance dispatch, not `.type` access (claims have no `.type`).
- `docker container inspect <missing>` prints `[]` with rc=1 — trust the exit code, never stdout.
- Docker Desktop on this host: `cmd //c start "" "...\Docker Desktop.exe"` silently fails (no process); launching the exe directly as a background process works. Daemon takes ~60–90s to come up.
- App.test.tsx `graphFetchCalls()` must exclude `/graph/visualization` and `/graph/expand` (they contain `/graph`) or legacy-route count assertions break once the viz fetch fires.
- Testing-library accessible-name gotcha: search-result rows concatenate the node-type `<kbd>` into the button name ("Dexter Morgan Character"); a plain name query matches the canvas stub button instead. Use `findAllByRole` + index, or match the concatenated name.
- Broad `sed -i 's/watchProgress.confirmedOrder/…/'` on identifier-heavy code rewrites unrelated call sites (broke `useGraph`'s null-skip semantics). Use patch with context, not global sed, for prop/identifier renames.
