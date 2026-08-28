# Structural Debt Map — retrieval/LLM/repository/graph layers (reviewed 2026-08-11)

Read-only thermo-nuclear review of `spoilerless/app/{retrieval,llm,repository,graph,cache,spoiler}`.
High-conviction structural findings with anchors, so a future task touching these
files starts from the canonical fix direction instead of re-deriving it.

## Duplication (highest-leverage dedups)

- **`_normalize` copied verbatim ×4**: `repository/change_set.py:166`,
  `repository/chat.py:36`, `repository/progress.py:30`, `repository/user.py:17`;
  divergent `_native` variant at `repository/user_content.py:57`;
  `RevisionRepository._from_json` overlaps. Canonical home: `graph/database.py`
  next to the driver.
- **`_hash_token`/`_generate_token` ×2**: `repository/session.py:96-101` and
  `repository/share.py:13-18`.
- **`_run_create` (user_content.py:70) vs `_run_apply` (change_set.py:583)** —
  same helper twice.
- **Visible-claim Cypher predicate+projection ×7**: `retrieval/tools.py`
  (`CLAIMS_FOR_FRONTIER_QUERY`, `GET_CLAIMS_QUERY`, `ALL_VISIBLE_CLAIMS_QUERY`,
  `GRAPH_SUMMARY_COUNTS_QUERY`) and `spoiler/filter.py` (`VISIBLE_CLAIMS_QUERY`,
  `SOURCES_QUERY`, `EVIDENCE_QUERY`). Fix direction: shared fragment builder
  `visible_claim_where(var)` + `claim_projection()`.
- **Boundary-existence check ×2**: `spoiler/filter.py:40` `BOUNDARY_QUERY` vs
  `repository/user_content.py:380` `BOUNDARY_VALIDATION_QUERY`.
- **Story-label inventory ×3**: `graph/seed.py:14` `NODE_LABELS`,
  `graph/setup.py:15` `STORY_LABELS`, `retrieval/tools.py:24`
  `STORY_NODE_LABELS`. Fix: one `graph/labels.py`.
- **Dual visibility audits**: `graph/seed.py:243` `audit_visibility_integrity`
  vs `graph/setup.py:18` `_check_visibility_schema` (different exclusion lists).

## Dead code (verified via cross-file grep)

- `retrieval/pipeline.py:90` `CONTEXT_SECTIONS` — never referenced (the
  9-section contract also lives in `llm/system_prompt.py:782` `CONTEXT_DELIMITERS`
  and hard-coded in `assemble_context`; fix: one `retrieval/context.py` registry).
- `retrieval/pipeline.py:69` `INSUFFICIENT_EVIDENCE_RESPONSE_TEMPLATE` — alias
  of an imported constant, unused.
- `retrieval/pipeline.py:72` `_fallback_for(question, ...)` — `question` unused.
- `llm/system_prompt.py:14` `SYSTEM_PROMPT_VERSION` — unused.
- `llm/provider.py:369/410/415` — `emitted` assigned, never read.
- `graph/database.py:96` `get_driver` — no callers (routes use `get_database`).

## Hot-loop special cases / parallel registries

- `retrieval/pipeline.py:395-532` — `TOOL_SCHEMAS` / `_TOOL_EXECUTORS` /
  `_TOOL_INPUT_MODELS` three parallel registries; `propose_changeset`
  hand-dispatched at 774-780, `get_user_notes` special-wrapped at 789-800.
  Fix: one `TOOL_SPECS` list, executor declares its result bucket.
- `repository/user_content.py:494-601` — shotgun label-variant loops
  (`for query in CUSTOM_NODE_*_QUERIES.values()`, up to 5 probes/request);
  six inline "capture old state" SELECTs at 522/569/620/666/725/772.
- `graph/candidates.py:182-202` — `approve_claim`/`reject_claim`/`edit_claim`
  identity pass-throughs of `execute_write(work, command)`.
- Python BFS duplicated: `retrieval/tools.py:360` `get_neighborhood`,
  `retrieval/tools.py:519` `find_path` (4-8 round trips; Cypher
  variable-length traversal is the fix direction).

## Layering notes

- `repository/user_content.py` embeds all Cypher inline; every other repository
  keeps queries in `graph/*.py` — the odd one out.
- `retrieval/pipeline.py:812` `_propose_changeset` instantiates a fresh
  `ChangeSetService` per tool call and re-resolves progress already resolved at
  turn start (line 625) — double DB read + potential boundary drift.
- `graph/progress.py:24` maintains `visible_until_order` as a third echo of
  `watched_through_order` on every write.
- `repository/session.py:308` `revoke()` uses ms `timestamp()` while all other
  Session timestamps are seconds epoch — mixed epochs on one node.
