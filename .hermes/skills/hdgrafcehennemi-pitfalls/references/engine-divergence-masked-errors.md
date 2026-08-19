# Engine divergence, masked DB errors, and select traps (PROB-09 sessions, 2026-08-11)

Captured while fixing PROBLEMS.md findings #61-#68 + the EIGHTH-PASS 503
class on 2026-08-11. Commits: 201f347..d7e47d1.

## Surfacing the real driver error behind a 503 DATABASE_ERROR

`core/errors.py::install_error_handlers` logs the ORIGINAL exception with
`logger.error("DATABASE_ERROR", exc_info=exc)` (errors.py:225) before
returning the sanitized 503 envelope — the underlying
`neo4j.exceptions.*` IS in the log, just not in the HTTP response.

To see it on a failing test:

```
uv run pytest spoilerless/tests/<file>.py -o log_cli=true --log-cli-level=ERROR
```

then grep the `neo4j.exceptions.` line directly under the `DATABASE_ERROR`
log record. Without this every DB failure looks identical (the envelope
masks the cause) and root-causing requires guessing.

## Neo4j engine divergence: local docker 5.x vs AuraDB (3 known classes)

1. **MERGE followed by MATCH without `WITH`** → `42N24 "WITH is required
   between MERGE and MATCH"` on local 5.x; the newer Aura engine tolerates
   it — the app 503s on local docker while Aura stays green. Fix: insert
   `WITH <vars>` between the MERGEs and the MATCH (valid on both engines).

   This was the ENTIRE EIGHTH-PASS change-set 503 class: 28 failures from
   one missing `WITH u, s` in `CHANGE_SET_CREATE_QUERY`
   (spoilerless/app/graph/change_set.py). When a whole test family 503s on
   local docker but passes on Aura, check every MERGE…MATCH adjacency
   FIRST. Exact repro:

   ```cypher
   MERGE (u:AppUser {id: $user_id})
   MERGE (s:Series {id: $series_id})
   WITH u, s                       -- ← required on 5.x
   MATCH (u)-[:HAS_CHAT_SESSION]->(session:ChatSession {...})
   ```

2. **Exact constraint/index name-set assertions** (`test_seed_idempotency`
   `test_community_schema_creates_only_unique_and_index`,
   `test_constraints_visibility_and_provenance`) — local 5.x generates
   different constraint names than Aura's engine. Write name-set
   assertions engine-agnostically or accept the local divergence.

3. **Seed-image class** (`test_graph_nodes_include_image_fields`,
   `TestSeedImageCuration::test_no_seed_image_for_resources_visible_above_order_one`)
   — fails on BOTH targets (seed data has zero character image_urls);
   pre-existing, not engine-related.

After the change-set WITH fix the full local docker suite runs ~2m and is
green except the 3 doc-contract + 2 seed-image + 2 constraint-name
classes — local docker is a viable full-suite target (Aura no longer the
only canonical runner).

## Radix Select swallows re-selected values (frontend)

Radix `Select` does NOT fire `onValueChange` when the clicked option equals
the currently-selected value. Consequence: if code programmatically
pre-sets a select's value (e.g. a series-switch resetting the episode
boundary to 1, so the episode selector already shows S01E01), the user's
FIRST click on that value is a silent no-op — no handler, no unlock modal,
and `App.test.tsx` e2e fails with
`Unable to find ... button "Yes, unlock episode"`.

Rule: never pre-set a select value that must remain clickable; if a reset
needs to leave the control in a pickable state, set the underlying state
to `null`/empty so the first click still fires a change event.

Debug signature: the selector displays the value but clicking it does
nothing; the test DOM dump shows the combobox `data-state="closed"` with
no modal rendered. (This was the real root cause of the #61 App.test
failures — the ledger's guess about a missing hook mock was wrong.)

## Bucket shape-sniffing mis-routes rows (retrieval pipeline)

`_accumulate` used `isinstance(result, list)` and wrapped EVERY bare list
as `{"nodes": ...}` — so `get_claims`/`get_evidence`/`get_sources` row
lists silently landed in the <nodes> context bucket (and `get_timeline`
episode rows polluted it too). Fix (commit adf2fb1, #63): executors
declare a `result_bucket` on their ToolSpec and the dispatcher wraps lists
into the declared bucket; `_accumulate` never sniffs shapes. When auditing
context assembly, verify each tool's rows land in the bucket the prompt
section expects.

## Refactor-wave workflow (what made the #62-#68 wave fast)

- Byte-identical copies → one helper: `neo4j_row_to_python` (4×
  `_normalize` copies), `run_single` (2× run→single→raise), `tokens.py`
  (2× hash/generate pairs) — all collapsed in commit 2846d3f (#68).
- Table-driven dispatch beats a giant match when rows differ only in
  query/targets/flags: `_APPLY_SPECS` (commit 5765168, #67) replaced a
  246-line 12-case match; per-op param builders stay because the queries
  genuinely use different param names ($node_id vs $claim_id vs $id).
- Fragment builders for repeated Cypher predicates: `visible_claim_where`
  + `claim_projection` (commit d5d94f7, #62) — 7 query constants compose
  from one definition; D-20 static scans still pass because the built
  strings contain the same gate lines.
- Shared traversal: `_walk_visible_claims` BFS (commit 6a64eec, #65) —
  get_neighborhood + find_path share one frontier/visited/parent walk with
  an `early_exit_ids` stop set.
- When a patch tool call mangles a file (duplicate import block, def
  glued to next class), rewrite the whole file with write_file instead of
  a third patch attempt — happened twice on repository/chat.py and
  focusReducer.ts.
