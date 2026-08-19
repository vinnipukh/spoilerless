# Spoiler threat-model fix phase (2026-08-10)

Companion to `references/spoiler-threat-model-verification-2026-08-10.md` (audit method). This file
records the verified fix-phase outcome: the 31 failures in
`.planning/tmp/verify-SPOILER-THREAT-MODEL.json` were resolved in `docs/SPOILER-THREAT-MODEL.md`
(170 → 209 lines; header/GSD marker preserved; implemented-vs-desired labels added everywhere; new
§4.9 rows P1–P6 for path/export/share surfaces; matrix gained a Status column).

## Fix-phase workflow (proven)

1. Batch-verify the load-bearing facts against the live tree BEFORE writing — do not just trust the
   verifier's "actual" text. In-process OpenAPI (`app.openapi()` — DB-free), `rg` symbol/line grabs,
   `sed` route-body reads, JSON seed inspection.
2. Validate every `pytest -k` selector before it goes into the doc:
   `rg -c "def test_.*(p1|p2)" spoilerless/tests/<file>` — a zero-match selector is a verifier
   failure waiting to happen. Substitute a real proxy and label the dedicated test Desired.
3. Write big docs in chunks with `<!-- PARTn -->` sentinels (per SKILL.md), then end with EXACTLY one
   trailing `\n`: chunked sentinel patches can leave multiple trailing blank lines at EOF, and
   `git diff --check` fails with "new blank line at EOF" (fix: patch the final row including the
   trailing newlines, re-run `git diff --check`).

## Live facts verified during the fix (2026-08-10)

- **Share surface (4 ops):** `POST /api/share` validates `visible_until_order` is a persisted episode
  (422 `INVALID_VISIBLE_UNTIL_ORDER`) but does NOT clamp it to the creator's persisted view/watched
  progress; `GET /api/share/{token}/graph` is unauthenticated (no user dependency), serves the STORED
  `record.visible_until_order`, reuses `fetch_graph` + cache-aside, 404 `TOKEN_NOT_FOUND` on
  invalid/expired/revoked. List/revoke are `CurrentUserDependency`-scoped. Never claim a share can't
  exceed the creator's own view — Desired mitigation, not implemented.
- **Boundary resolution:** `_resolve_effective_boundary` api/graph.py:129 — anonymous FIXED at 1
  (persisted-episode check resolves against the effective, not requested, order → no episode-id
  probing above 1), authenticated clamped to `min(requested, view_as_of_order)` then
  `effective_view_order(view, watched)`. Used by GET /graph, POST /graph/path (server-injected
  `MAX_PATH_HOPS`=4 as requested order), GET /export (`visible_until_order` default 1).
- **Working matrix selectors (all ≥1 match at HEAD):** `-k "hidden or visible"`, `"relationship or
  edge"`, `"edge or hidden"` (test_graph_api.py); `"claim"`, `"evidence"`, `"search"`, `"count or
  summary"`, `"path"`, `"source or locator"` (test_retrieval_tools.py); `"title"`/`"mask"`/
  `"synopsis"`/`"runtime"` (test_episode_masking.py, test_spoiler_policy.py); `"stale"`
  (test_change_set_confirmation.py — NOT test_change_set_api.py, which has zero stale tests);
  `"order"` (test_progress_api.py, test_episode_ordering.py); `"not_found"`; `"cache"`; `"session"`;
  `"export"`; `"source"` (test_citations.py). **Zero-match at HEAD:** `degree`, `layout`, `timing`,
  `autocomplete`.
- **Refreshed line anchors (doc citations drifted):** `mask_episode_metadata` policy.py:154;
  `find_path` tools.py:519; `search_entities` tools.py:476; `SEARCH_ENTITIES_QUERY` tools.py:135;
  `ChangeSetStale` repository/change_set.py:75; `CHANGESET_STALE` api/change_set.py:61; confirm
  admin-gated (`RequireAdminDependency`) api/change_set.py:116; `GraphNode` domain/graph.py:11;
  `ensure_progress_for_chat` services/chat.py:226; `_resolve_or_create_progress` services/chat.py:237;
  `answer_stream` services/chat.py:278; snapshot repository/chat.py:135,154 + domain/chat.py:71.
- **Contract test drift:** `test_openapi_contract.py:202` pins `len(schema["paths"]) == 32` — stale
  vs HEAD's 37 (test_frontend_contract_doc.py:105-106 asserts 50 ops / 37 templates), so that file
  fails against HEAD until refreshed. The doc's X1 row flags it; do not claim it as a green gate.
- **Seed media fields:** exactly 0 characters carry `image_url`; 6 carry `image_source_url` only
  (dexter_morgan, debra_morgan, angel_batista, maria_laguerta, james_doakes, rita_bennett — all
  `visible_from_order:1`, `image_url: None`). Attribution URLs are NOT image assets.
