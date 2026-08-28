# 10-07 Focus Contract / Answer Graph — pitfalls + resume state

Phase 10 plan 10-07 (GraphRAG focus → temporary Answer Graph + Evidence Chain).
Backend Task 1 mostly built; frontend Task 2 + SUMMARY pending (executor hit tool cap, handoff returned).

## What was built (uncommitted at handoff)

- `spoilerless/app/retrieval/pipeline.py`: `GraphRagFocusContract` (dataclass) +
  `build_graphrag_focus(retrieved, node_ids, edge_ids)` — pure classifier of this
  turn's focus ids into entity/event/investigation/edge/dropped, validated ONLY
  against this turn's retrieved set (never a fresh DB check). `_finalize` routes
  the final `done.graph_focus` through it.
- `spoilerless/app/services/visualization.py`: `project_graphrag_focus(graph,
  focus_ids, events=None)` maps micro/supporting Event focus ids to the episode's
  visible major Events (deterministic `(vfo, id)` order) + a timeline entry
  (Inspector detail); `project_view` threads `events` to the graphrag_focus branch.
- `spoilerless/app/api/graph.py`: `get_visualization` now calls
  `project_view(result, view, events=None, focus_ids=focus_id)` — the editorial
  `SafeEventContext` seam is None in production (no event source wired yet).

## Pitfalls

- **Wire shape is frozen**: `GraphFocus` in `spoilerless/app/domain/chat.py` is a
  StrictModel `{node_ids, edge_ids}` — never add classification keys to the done
  event. The contract (`build_graphrag_focus`) is a separate pure helper; only
  `entity_ids`/`edge_ids` ride the wire.
- **event_ids ⊆ entity_ids**: concatenating both into `done.graph_focus.node_ids`
  duplicates ids — `entity_ids` alone is the complete node focus. (Introduced and
  fixed during 10-07 Task 1; regression-test it.)
- **Focus reference must resolve INSIDE the DTO** after micro-event substitution:
  primary = first canonical id that survived → its substituted major event →
  first kept node. `VisualizationDTO.enforce_dto_references` rejects anything else.
- **Checked-in fixtures have only major events**: `s01e01_safe.json` /
  `s01e02_cumulative_safe.json` events are all `tier: major`. Micro-event tests
  append synthetic `GraphNode` + `SafeEventContext` rows (synthetic fixtures are
  allowed; never series_dexter real rows).
- **FakeLLMProvider yields the same scripted event list EVERY call**: one list
  containing `tool_call` + `done` still terminates — round 2 dedupes the tool call
  (`new_calls` empty → finalize with the done event). Use
  `test_retrieval_pipeline.py`'s `_CallScriptedProvider` for per-call lists.
- **CLOSE_TEMPORARY gap (Task 2 must fix)**: `useSceneState.ts` snapshot restores
  camera/selection/expansions/timelineSelection only; Task 2 acceptance also
  requires filters + active view restored. Extend `TemporarySnapshot`/
  `takeSnapshot`/`CLOSE_TEMPORARY`.
- **App.tsx does not use useSceneState**: the scene reducer is standalone (tests
  only); App manages its own useState (topTab/mode/selectedElement). Task 2 needs
  an explicit OPEN_TEMPORARY/CLOSE_TEMPORARY wiring decision — Answer Graph as an
  overlay keeps the canvas mounted (10-05 pattern: never unmount/relayout).
- **search_files/read_file with backslash absolute Windows paths fails** (rg path
  translation, `os error 3`): use repo-relative paths from the repo root.

## Resume state

- Handoff: backend Task 1 edits uncommitted. Next: create
  `spoilerless/tests/test_visualization_graphrag.py` (FakeLLM + stub DB only — no
  live provider/keys/Neo4j; `_StubDatabase` routes by distinctive Cypher
  fragments, SUPPORTED_BY/REFERS_TO BEFORE `claim.claim_type`), run
  `unset PYTHONPATH && uv run pytest spoilerless/tests/test_visualization_graphrag.py -q`
  plus the touched suites (`test_retrieval_pipeline.py`,
  `test_visualization_projection.py` — signature is backward-compatible), commit
  Task 1, then frontend Task 2 (EvidenceChain.tsx, AnswerGraph.tsx, App.tsx,
  useSceneState snapshot extension), `npm --prefix frontend run build`, SUMMARY.
- Shared requirement IDs VIZ-03/VIZ-10 (with 10-08): do NOT mark complete here.
- UAT backstops for the SUMMARY coverage block: UI-RESP-01, UI-GESTURE-01,
  UI-TEXT-01, UI-A11Y-01, UI-RESTORE-01 as `human_judgment: true`.
