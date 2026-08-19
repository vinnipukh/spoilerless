# Phase 7 (v1.2) plan-check — verified facts & checklist (2026-08-03)

Context: gsd-plan-checker review of `.planning/phases/07-spoiler-safety-hardening/`
(07-01..07-08-PLAN.md, 8 plans). Verdict: **1 BLOCKER + 7 WARNINGS**. All facts
below were re-verified against live source on 08-03 — re-check before trusting
after Phase 7 executes (they describe the pre-execution state).

## The boundary formula rule (the one blocker)

D-05 invariant: `effective = min(view_as_of_order, watched_through_order)`, never
overridable by frontend or LLM. The fail-closed resolution on ANY public surface is:

```
effective = min(requested/visible_until_order, persisted_view_as_of_order, persisted_watched_through_order)
```

- 07-02 Task 3 described `policy.effective_view_order(requested_view, persisted_watched_through_order)`
  with "a client asking above the persisted view boundary is clamped to the persisted
  watched_through_order" → yields `min(requested, watched)`, omits the persisted view.
  view=1 / watched=3 / request=3 → effective 3 → Episodes 2-3 leak to a viewer of Episode 1.
  Also self-contradictory within one sentence (first clause says clamp by view semantics).
- The plan's own acceptance test only covered request==view (view=1 → effective 1), so
  the leak path was untested — the classic hidden-leak pattern.
- Review rule: grep plan text for `effective_view_order(` calls and "clamped to ...
  watched" phrasing; require the persisted view in the min + a request-above-view test.
- Episodes route (07-03 Task 2) had the reverse omission: effective from persisted
  (view, watched) WITHOUT the requested order → a request below the persisted view
  over-returns (is_unlocked=True above the requested boundary). Lower severity (content
  up to watched is not spoiler-bearing) but still wrong per D-21 display semantics.

## Verified symbol inventory (backend, 08-03)

`backend/app/spoiler/filter.py` query constants: BOUNDARY_QUERY, EVIDENCE_QUERY,
NODES_QUERY, SERIES_BY_ID_QUERY, SERIES_EPISODES_QUERY, SERIES_LIST_QUERY,
SERIES_QUERY, SOURCES_QUERY, STRUCTURAL_EDGES_QUERY, VISIBLE_CLAIMS_QUERY,
VISIBLE_USER_RELATIONSHIPS_QUERY.

`backend/app/retrieval/tools.py` query constants: ALL_VISIBLE_CLAIMS_QUERY,
ALL_VISIBLE_NODES_QUERY, CLAIMS_FOR_FRONTIER_QUERY, EPISODE_CODES_QUERY,
EVIDENCE_FOR_CLAIMS_QUERY, GET_CLAIMS_QUERY, GET_ENTITY_QUERY, GET_EVIDENCE_QUERY,
GET_SOURCES_QUERY, GRAPH_SUMMARY_COUNTS_QUERY, NODES_BY_IDS_QUERY,
SEARCH_ENTITIES_QUERY, SOURCES_FOR_CLAIMS_QUERY, TIMELINE_QUERY, USER_NOTES_QUERY.

Key behaviors (line numbers as of 08-03):
- `GraphService.resolve_boundary(series_id, visible_until_order)` (services/graph.py:39)
  only VALIDATES the order against BOUNDARY_QUERY (persisted episode) — today the client
  can request any persisted order; the graph does not cap by persisted progress.
- `SERIES_EPISODES_QUERY` has NO boundary parameter (the 07-01 audit's expected gap;
  07-03 adds masking + the `visible_until_order` query param).
- services/chat.py: `ensure_progress_for_chat` (line 161), `_resolve_or_create_progress`
  (line 172) — returns persisted boundary, auto-creates order-1 row on missing progress.
- `ChangeSetStale(RuntimeError)` at repository/change_set.py:74; apply-staleness today
  compares against since-lowered progress (07-07 Task 2 extends it to compare the
  ChangeSet's `visible_until_order_snapshot` vs the CURRENT effective boundary → 409
  `changeset_stale`). `ChangeSetResponse.visible_until_order_snapshot` at
  domain/change_set.py:274.
- domain/change_set.py header comment: "No operation model EVER declares origin,
  visible_from_order, ..." — client-supplied visibility is ALREADY structurally
  forbidden; 07-07 Task 2's "schema gains no client-supplied visibility field" is
  consistent with existing design.
- api/user_content.py: `list_notes`/`get_note`/`get_custom_node`/`get_custom_relationship`
  take `visible_until_order: Boundary` (Annotated int, gt=0).
- llm/system_prompt.py: `CONTEXT_DATA_FRAMING` present + `SYSTEM_PROMPT_ENG`/`SYSTEM_PROMPT_TR`
  (user-owned prose — plans must never edit; only CONTEXT_DATA_FRAMING may change, then
  re-run test_prompt_injection.py).
- Contract baseline: 33 path templates / 45 (method,path) ops; full-suite baseline
  failures = test_seed_idempotency.py x3, test_extraction_models.py::TestSchemaArtifact x2,
  test_candidate_ingest.py x4 errors, test_candidate_review.py x3 errors (name-set match,
  never count-only). Lint baseline 28 errors.

## Verified seed-data facts (08-03)

- `data/dexter/metadata/episodes.json`: 3 episodes (Dexter/Crocodile/Popping Cherry),
  episode_order 1/2/3, visible_from_order 1/2/3. NO title_is_spoiler fields yet —
  07-03 Task 1 adds them (S01E01 non-spoiler from 1; E02/E03 spoiler at their order).
- **`data/dexter/metadata/characters.json` does NOT exist.** Character seed lives at
  `data/dexter/seed/characters.json` (with claims.json, events.json,
  evidence_fragments.json, locations.json, sources.json). 07-06 Task 3 pointed at the
  metadata/ path (WARNING) — any plan referencing "characters.json" must use seed/.
- `data/dexter/seed/characters.json` carries `image_url` for 9 characters, incl. THREE
  with `visible_from_order > 1`: paul_bennett (2), rudy_cooper (3), harry_morgan (3).
  ⇒ A "no resource with visible_from_order > 1 carries image_url" curation test FAILS
  against current seed unless those URLs are nulled — that data edit must be in the
  plan's files_modified explicitly.
- image_url also referenced in backend/app/domain/graph.py + spoiler/filter.py (the
  media leak channel is real; 07-06's premise holds).

## Frontend facts (08-03)

- `frontend/src/api/progress.ts`: `updateProgress(seriesId, visibleUntilOrder)` POSTs
  `{visible_until_order}` only; `UserSeriesProgress` type mirrors only that field.
  ANY plan whose behavior list requires POSTing watched_through_order/view_as_of_order
  (07-03 Task 3) must include this file — it was omitted (WARNING).
- `frontend/src/api/series.ts` `getEpisodes(seriesId)` (line 8) — no order param yet.
- `frontend/src/components/episode/`: EpisodeSelector.tsx, ConfirmAdvanceModal.tsx +
  ConfirmAdvanceModal.test.tsx, SeriesSelect.tsx. **NO EpisodeSelector.test.tsx** —
  a plan treating it as an "existing regression gate" is wrong; it's created by the plan.
- App.test.tsx lives in `frontend/src/` root. DetailPanel.tsx + DetailPanel.test.tsx exist
  (avatar fallback ~lines 42-68 per 07-06). useWatchProgress.test.ts exists.
- `visible_until_order_snapshot` on chat messages: repository/chat.py:133/151 +
  domain/chat.py:53 (the CHAT-03 snapshot carrier is real).

## Plan-review checklist for hdgrafcehennemi plan sets (reusable)

1. Boundary formulas: `min(requested, persisted_view, persisted_watched)` everywhere;
   flag two-arg `effective_view_order(requested, watched)` / "clamped to watched" prose.
2. Frontend API-client files match behavior lists: grep `frontend/src/api/*.ts` for the
   payload shape the plan's tests must POST; missing file = wiring gap.
3. Seed paths: `data/dexter/seed/` (not `metadata/`) for characters; verify any
   curation/masking test against ACTUAL seed values (image_url + visible_from_order).
4. Query-constant names exist per file (inventory above); `SERIES_EPISODES_QUERY` is the
   boundary-unaware surface.
5. Run `gsd-tools verify.plan-structure` per plan (native Windows path + cygpath -w);
   `valid:true` + warnings = missing `<files>` (12 tasks across 07-01/07-05 T3/07-06 T3/
   07-07 T3/07-08 T1-3).
6. VALIDATION.md gate: `.planning/config.json` has `nyquist_validation: true`; the 06
   phase shipped `06-VALIDATION.md`; a phase dir without `*-VALIDATION.md` trips role-skill
   Dimension 8 Check 8e (regenerate via `/gsd-plan-phase <N> --research` or explicit waiver).
7. Contract inventory: plans changing only response shapes must be additive and keep the
   33/45 baseline; no route adds ⇒ no contract-file edits, but prove it by running
   test_openapi_contract.py + test_frontend_contract_doc.py.
8. Scope: 3 tasks/plan is the norm here; files_modified 15-19 (07-03=17, 07-07=19) is
   borderline-BLOCKER per the generic threshold but matches Phase-6 precedent — WARNING.
