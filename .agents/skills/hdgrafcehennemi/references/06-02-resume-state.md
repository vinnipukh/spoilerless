# Plan 06-02 resume state (interrupted session — work INCOMPLETE)

Plan: `.planning/phases/06-spoiler-safe-graphrag-chat-and-graph-editing-agent/06-02-PLAN.md`
(3 tasks, all `tdd="true"`). Branch: `feature/spoiler-safe-graphrag-agent`.

**HEAD: `9e1ba49` — dirty: `backend/app/retrieval/pipeline.py`** (Task 2 GREEN half-applied).
Per the GSD close-out invariant this is an illegal partial state (production
commits exist, no SUMMARY.md) — resume immediately; do NOT re-dispatch from
scratch.

## Commits so far (real SHAs)

- `4418d09` test(06-02): add failing tests for eight retrieval tools and leakage matrix
- `5c3bff1` feat(06-02): add remaining eight allowlisted retrieval tools
- `9e1ba49` test(06-02): add failing pipeline hardening tests (dedup, ordering, bounds, round limit)

## Uncommitted work — Task 2 GREEN (finish this first)

`backend/app/retrieval/pipeline.py` currently defines `assemble_context` TWICE:
- NEW version at ~line 133 (9-entry CONTEXT_SECTIONS, `_entity_line`/`_edge_line`/...
  formatters, `_dedupe_by_id`, `_by_distance`, new `assemble_context` with
  `edges`/`series`/`boundary` params).
- OLD 6-section version still present at ~line 404. The old def wins → tests
  still RED. Steps:
1. Delete the old `assemble_context` block (~lines 404-467) — grep
   `-n "def assemble_context"` first.
2. Wire `_finalize` to pass `edges=retrieved["edges"]`, `boundary=boundary`, and
   `series` (fetch `SERIES_QUERY` from `backend/app/spoiler/filter` when
   `self._database is not None`, else fall back to `{"id": series_id}` — the
   `database=None` prompt-injection test path must not touch the DB).
3. Update `backend/app/llm/system_prompt.py`: `CONTEXT_DELIMITERS` and
   `SYSTEM_PROMPT_V1` must name ALL 9 tags
   (`test_system_prompt_names_delimiters_and_frames_content_as_data` asserts
   every delimiter literal appears in the prompt).
4. Add `distance` annotation in `get_neighborhood` (tools.py): claims get their
   BFS level, nodes their discovery level, evidence/sources inherit their
   claim's level — makes the direct-evidence prioritization real end-to-end.
5. Verify: `cd backend && uv run pytest tests/test_retrieval_pipeline.py
   tests/test_prompt_injection.py -x` → expect all pass (21 tests).
   Commit: `feat(06-02): harden context pipeline (dedup, ordering, bounds, auth exclusion)`.

## Remaining after Task 2 GREEN

- **Task 3 (TDD)** — new `backend/tests/test_citations.py`:
  - RED tests: citation to real-visible-but-unretrieved-this-turn claim
    rejected (Pitfall 3 exact case); hidden claim/evidence/source citation
    rejected; zero surviving citations → content replaced by
    `INSUFFICIENT_EVIDENCE_RESPONSE_TEMPLATE` + empty list; byte-identical
    response for does-not-exist vs hidden entity, and 1-order-beyond vs
    many-orders-beyond; no "you haven't met them yet" phrasing; citations
    render in retrieval order (model cites [B, A] → output [A, B]).
    Commit `test(06-02): ...`.
  - GREEN: `INSUFFICIENT_EVIDENCE_RESPONSE_TEMPLATE` constant (keep
    `INSUFFICIENT_CONTEXT_ANSWER` as alias), sort surviving citations by
    retrieval position, add fixed-template instruction + no-hidden-hint rule to
    SYSTEM_PROMPT_V1. Commit `feat(06-02): ...`.
  - Verify: `cd backend && uv run pytest tests/test_citations.py -x`.
- **Full suite:** `cd backend && uv run pytest -q` — expect ONLY pre-existing
  failures (test_candidate_ingest/test_candidate_review: missing
  `data/dexter/test/extraction_fixture.json`; test_seed_idempotency: drift) —
  confirm zero NEW failures.
- **SUMMARY:** write
  `.planning/phases/06-spoiler-safe-graphrag-chat-and-graph-editing-agent/06-02-SUMMARY.md`
  (template: the 06-01-SUMMARY.md in the same dir) and commit IMMEDIATELY
  (no narrative between write and commit) as `docs(06): summary for 06-02`.
  Never commit `.planning/config.json` / STATE.md / ROADMAP.md.

## Seed test IDs (useful for Task 3)

- Entities: `dexter:character:{dexter_morgan, debra_morgan}` (order 1),
  `paul_bennett` (order 2), `harry_morgan`, `rudy_cooper` (order 3).
- Claims: `dexter:claim:s01e01:dexter_debra_family`,
  `dexter:claim:s01e01:dexter_batista_work`,
  `dexter:claim:s01e01:doakes_distrusts_dexter` (all order 1),
  `dexter:claim:s01e03:dexter_harry_family` (order 3, hidden at boundary 1).
- Evidence `dexter:evidence:s01e01:01`; sources `dexter:source:s01e0{1,2,3}`.
- get_neighborhood(DEXTER, boundary 1) claim order (ORDER BY
  visible_from_order, id): batista_work < debra_family < doakes_distrusts.
