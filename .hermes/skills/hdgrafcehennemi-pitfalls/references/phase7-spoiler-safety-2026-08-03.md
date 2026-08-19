# Phase 7 spoiler-safety execution notes (2026-08-03)

## HTTP 429 rate-limit executor deaths — the proven recovery pattern

gsd-executor subagents (via delegate_task) died 5× this session at
`HTTP 429: Hold up for a bit, you've exceeded the rate limit on your API key`
— always MID-PLAN, leaving uncommitted partials in the tree. Recovery loop
(proven on 07-02 and 07-03):

1. NEVER trust the async return — check `git log --oneline -5`, `git status --short`,
   and whether `*-SUMMARY.md` exists FIRST.
2. Judge the uncommitted tree: run the plan's named test files. A partial that
   breaks callers (e.g. graph/progress.py Cypher gained `$watched_through_order`
   params no caller passed → every progress write red) must be REVERTED
   (`git checkout -- <file>`) and re-verified before re-dispatch.
3. Re-dispatch with: "CONTINUE from here — Task N is committed as <sha>, do NOT
   redo it" + every root-caused env fact baked in + "minimize tool calls, batch
   reads, run named tests ONCE, commit immediately after green, if you approach
   the limit STOP and hand off".
4. After TWO deaths on the same plan, finish the remainder INLINE (orchestrator).
   07-02 Task 3 and 07-03 Task 3 were both finished inline successfully.

Interrupted runs also leave test-created nodes on the SHARED live Neo4j
(orphaned `UserSeriesProgress`/`Session` rows with no owning `:AppUser`) that
break the seed integrity audit for later fixtures. Clean orphaned rows before
rerunning: `MATCH (p:UserSeriesProgress) WHERE NOT EXISTS { MATCH (:AppUser
{id: p.user_id}) } DETACH DELETE p` and `MATCH (s:Session) WHERE NOT EXISTS {
MATCH (:AppUser)-[:HAS_SESSION]->(s) } DETACH DELETE s`. NEVER delete rows
owned by the real dev user (`user:ae8a41b7-db96-40e8-b6c2-2e3c69aedb11` —
has progress + chat session on series_dexter).

## THE GRAPH-EDIT TOOL GAP (user-verified 08-03 — still open until 07-07 lands)

The chat agent answers "I can't add or create relationships or nodes myself"
CORRECTLY. Root cause: `TOOL_SCHEMAS` (backend/app/retrieval/pipeline.py:330)
ships 11 read-only retrieval tools and `services/chat.py:295` hardcodes
`proposed_change_set=None`. `ChangeSetService.propose` (services/change_set.py:154),
`POST /api/series/{series_id}/change-sets`, and the frontend ChangeSetCard
confirm/reject UI all exist — only the LLM bridge was never built (Phase 6 gap).
07-07 Task 2 now plans the 12th allowlisted tool `propose_changeset` (input
mirrors the domain/change_set.py op union; result rides the done-envelope's
`proposed_change_set`; system prompt prose untouched — capability advertised via
the tool description). Do NOT tell the user the agent can propose graph edits
until that tool exists.

## Seed integrity audit exclusions (07-02)

`audit_visibility_integrity` (backend/app/graph/seed.py) fails on ANY
series-scoped node with null `visible_from_order` — EXCEPT `UserSeriesProgress`
and `ChatSession` (per-user state carrying split-boundary fields /
`visible_until_order_snapshot`, not story reveal-points). Adding more
user-state labels later requires updating the exclusion list.

## Progress model post-07-02 (durable facts)

- `UserSeriesProgress` carries `watched_through_order` + `view_as_of_order` +
  `visible_until_order` (backward-compatible effective echo). `ProgressService.resolve()`
  returns the policy-computed `effective_view_order`; `upsert` enforces
  `1 <= view <= watched` via `assert_visibility_invariants`.
- `ProgressUpdateRequest` accepts `watched_through_order` OR legacy
  `visible_until_order` (confirm), `view_as_of_order` alone = view-only change
  that never lowers watched (PROG-01).
- Graph GET (api/graph.py): optional-user clamp — `effective = min(requested,
  persisted view, persisted watched)` via `get_optional_current_user` (deps.py,
  never raises); anonymous callers keep legacy behavior; `GraphResponse` echoes
  `effective_view_order`.
- Frontend `useWatchProgress`: `confirmedOrder` IS the current view
  (`viewAsOfOrder`) — existing consumers stay correct; `watchedThroughOrder` is
  separate. Selecting `<= watched` is view-only (no modal, view-only POST);
  `> watched` opens the unlock modal with "Episodes 1 through N will be
  considered watched" copy (D-06). App.test's `decreaseProgressToS01E01` helper
  no longer clicks the modal.
- Episode masking: episodes route optional `visible_until_order`; services/series.py
  → `policy.mask_episode_metadata`; `EpisodeResponse` gains display_title /
  is_unlocked / is_current_view; data/dexter/metadata/episodes.json carries
  title_is_spoiler / title_visible_from_order.

## GSD plan-editing quirks (hit this session)

- decision-coverage gate parse: CONTEXT.md decision bullets MUST be
  `- **D-NN:** text` (colon after D-NN). Without the colon the gate returns
  `passed: false` / `could-not-parse` with 0 decisions, even though the plan
  covers everything.
- `roadmap.get-phase` / `init.plan-phase` need the phase declared as a
  `#### Phase N: Name` heading (h2–h4) with `**Goal:**` bold — a bare bold
  `**Phase N:**` line or plain `Goal:` is invisible (`phase_found: false`,
  `expected_phase_dir` null).
- `verify.plan-structure` "forbidden literal" errors: a negative-grep acceptance
  criterion (e.g. `grep -c "propose_changeset" ... >= 2` paired with
  `grep -c "X=None" ... == 0`) whose literal appears in the plan body is
  rejected — add `<!-- planner-discipline-allow: <literal> -->` markers in the
  frontmatter when the literal must legitimately appear.
- Tracking verbs: `state.begin-phase`, `state.planned-phase`, `phase-plan-index`;
  never hand-edit STATE.md (milestone-switch rewrites frontmatter + body).
