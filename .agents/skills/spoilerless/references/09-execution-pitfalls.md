# Phase 09 execution lessons (multi-agent deaths, inline completion, test-drift)

Session 2026-08-05, plans 09-04/09-07/09-09 executed after repeated subagent
429/503 deaths. Three distinct death classes, three distinct recoveries.

## User directive on subagent 429s (durable preference)

After the third executor died on `HTTP 429: ... exceeded the rate limit`,
the user said: **"refrain from using subagents, do the work yourself if
needed, i believe that may be causing your 429's"** — then re-allowed
subagents once the current plan (09-04) was fulfilled inline ("ok you may
try the subagent's after task 4 is fulfilled").

Pattern for this user/repo:
1. Subagent dies 1× (any cause) → disk-first verify, normal recovery.
2. Subagent dies 2×+ in a row on 429/503 → STOP dispatching; finish the plan
   inline yourself (read plan → edit → run verify → commit → SUMMARY).
3. Resume subagents only for the NEXT plan after the inline one is closed.
Parallel subagent model calls amplify upstream rate limits — one in-context
executor does not hit them.

## Death-class recovery (disk-first, always)

| Death class | Signal | Recovery |
|---|---|---|
| Read-only | died after only reads, tree clean | re-dispatch SAME plan fresh (nothing to resume) |
| GREEN partial | commits landed OR uncommitted tree passes the plan's suites | commit as-is immediately (clobber-guard), then scoped continuation for remaining tasks only |
| UNCOMMITTED red partial | executor died mid-edit, tests fail | do NOT commit — classify failures (below), fix inline, then commit with honest message naming the executor partial |

## Test-drift vs code-bug classification (fail-closed contract changes)

When a security/read-path contract change lands (09-03 auth-gate, 09-04
anonymous-boundary clamp), existing tests probing the OLD behavior fail.
Classify BEFORE touching product code — these are almost always TEST drift:

- **401s on previously-anonymous calls** → auth-gate fallout. Add a
  `user_session` fixture (copy `_create_user_with_session`/`_delete_test_user`
  from `test_candidate_review.py` — module-local, never assume a shared one;
  check `grep -rn "def user_session" spoilerless/tests/`).
- **Boundary-2/3 probes returning effective 1** → anonymous clamp. Authenticate
  with a boundary session whose `watched_through_order` matches the probe.
  Parameterized fixture pattern (`_prepare_boundary_session(watched_through)`
  in `test_graph_api.py`: AppUser + HAS_PROGRESS + HAS_SESSION via raw Cypher,
  fresh random token per run so the Session token_hash unique constraint can't
  collide, cleanup in finally). Same class hit `test_episode_masking.py`.
- **422 expectations on anonymous probes of non-persisted orders** → after the
  clamp, an anonymous order-4 request returns 200/effective-1 (can't probe);
  the 422 non-persisted check must move to an AUTHENTICATED request.

## Two real bugs found inline (both my own/executor code, not tests)

1. **Neo4j sweep units bug**: `expires_at`/`created_at` are stored as SECONDS
   epoch (`time.time()`), but the documented sweep Cypher used
   `s.expires_at < timestamp()` — Neo4j `timestamp()` is MILLISECONDS, so
   every session matched "expired" (test failed `removed == 3` vs `2`, live
   session deleted). Fix: compare against `$now` param = `time.time()`.
   Session `get()` already used `$now`; keep all time comparisons in the same
   unit (seconds). Never mix Cypher `timestamp()` with Python-epoch fields.

2. **`useRevisions.test.tsx` typecheck break from "no-explicit-any" typing**:
   typing `let captured: any` → `ReturnType<typeof useRevisions> | null`
   broke tsc -b with TS18047 (null in closures) + TS2339 (`.data`/`.error`
   don't exist on all discriminated-union members). `npm run build` is the
   ONLY typecheck that catches this (tsc -b includes test files; plain
   `tsc --noEmit` skips referenced projects — vitest green ≠ typecheck
   green). Fix: narrowing helpers (`dataOf`/`errorOf` with a `status ===`
   check) or `Extract<Union, {collection:'nodes'}>` row variants. Use
   `captured!` for the null part; discriminated union needs real narrowing.

## react-refresh/only-export-components (eslint error, not warning)

Moving `NODE_TYPES`/`NodeTypeMeta` OUT of `GraphLegend.tsx` into
`frontend/src/lib/nodeTypes.ts` — a components-only file cannot export
constants (`react-refresh/only-export-components`). Component re-exports
(`NodeSwatch`) are fine; constant exports are not. After moving, re-point ALL
importers (`rg -n "NODE_TYPES" frontend/src`): NodeSearch + CommandPalette
both imported from GraphLegend.

## Research "already done" claims need live verification

RESEARCH.md claimed "#42 NameError already fixed in tree" — the 09-02
executor found it was STILL LIVE (`google` not bound in
`ProductionGoogleVerifier.verify` scope) and fixed it for real (`a36676a`).
Rule: verify each research "already fixed/gone" claim against the live tree
before planning around it; a claim can be stale by hours if a sibling agent
is also working the repo.

## Frontend mirror of the FastAPI 422 detail array (type widening, 09-05)

`frontend/src/api/client.ts` normalizes FastAPI validation errors: the
constructor accepted `ApiErrorDetail | Array<{ msg?: string }>`, but real
422 bodies carry `{loc, msg, type}` entries — a test passing a full item
(`{loc: [...], msg, type}`) failed `tsc -b` with TS2353 ("'loc' does not
exist"). Fix: export `ApiValidationErrorItem = { loc?: (string|number)[];
msg?: string; type?: string }` and type the constructor against
`ApiErrorDetail | ApiValidationErrorItem[]`. Keep the FE mirror of the
backend error envelope explicitly typed — the array shape is the one place
where "detail" is NOT `{code, message}`.

## Closeout-only budget death → finish inline, do NOT re-dispatch

Executor deaths often land at the very END of a plan (all tasks committed,
only SUMMARY.md + tracking + closeout verification left). Resuming that with
a fresh executor costs a full spawn for ~4 tool calls. Read the resume state
from the subagent summary file (`subagent-summary-*.txt` — its "Remaining /
resume here" block is the exact spec), then:

1. Commit any un-staged green partials with an honest message naming the
   executor (`... — executor partial committed inline (verified N/N, gate 0)`).
2. Re-run the plan's named verify commands yourself (that IS the closeout
   verification — pytest target + vitest + `npm run build` + lint + grep gates).
3. Write SUMMARY.md covering all tasks with per-task SHAs, commit + tracking.

Also: when a continuation IS needed, embed the dead executor's exact
remaining-work notes VERBATIM into the dispatch context (they already did the
file-by-file analysis; re-deriving it wastes calls and invites drift). The
09-05 continuation succeeded on this pattern.

## Other inline-completion notes

- `npm run build` chunk-size warning is pre-existing/benign.
- After inline edits, run BOTH vitest AND `npm run build` AND `npm run lint`
  (lint catches react-refresh; build catches TS2339/TS18047 in test files).
- MSYS python-heredoc `re.sub` backreferences (`\1`) corrupt YAML frontmatter
  with SOH 0x01 bytes — rewrite the whole line, never preserve matched eol;
  byte-verify with `od -c`. (Bite twice: 09-15 wave sync.)
- `git status` right before a staged commit: the avatar-sanitization fix
  (`services/auth.py`) was nearly left behind because the stage list was built
  from the subagent summary, which listed it under trust nits without the
  exact path. Diff the remaining dirty files after staging, not just before.
