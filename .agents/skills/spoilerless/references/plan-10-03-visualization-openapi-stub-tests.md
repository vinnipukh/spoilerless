# Plan 10-03 learnings: visualization route, locked-inventory updates, stub-client tests

Session: resuming plan 10-03 (typed visualization route + cache epochs) on the Windows host.
All items below are VALIDATED by passing pytest runs in that session unless marked otherwise.

## Windows host: search_files vs read_file/terminal

- `search_files` (ripgrep-backed) FAILS on this host with MSYS-style paths:
  `rg: /c/Users/...: IO error ... Sistem belirtilen yolu bulamıyor. (os error 3)`
  It also errors on regexes containing `{`/`}` quantifiers (e.g. `^## |50|37`).
- Workaround that works: `read_file` with native Windows paths (`C:\Users\arhan\...`)
  for content reads, and `terminal` (`grep -nE`, `ls`) for pattern search. Do not burn
  attempts retrying search_files with `/c/...` paths — switch immediately.
- Prefer `read_file` pagination over `grep` when you need surrounding context; use
  `grep -n` when you only need line numbers/anchors.

## OpenAPI "locked inventory" triple-update (adding any route)

Adding one route means updating THREE places in the SAME task commit (contract tests
fail otherwise — this is a locked inventory by design, not a bug):

1. `spoilerless/tests/test_openapi_contract.py` — `expected_paths` set, the
   `(method, path)` methods set, and `assert len(schema["paths"]) == N`.
2. `spoilerless/tests/test_frontend_contract_doc.py` — `EXPECTED_OPERATIONS` set and
   `assert len(documented) == len(generated) == N` / `len(EXPECTED_TEMPLATES) == M`.
3. `docs/reference/frontend-api-contract.md` — the `## Exact OpenAPI operation inventory`
   table row AND the "**N method/path operations over exactly M unique path templates**"
   sentence. Optionally add a route section + boundary bullet near
   `## Spoiler boundary and fail-closed reads`.

Example: 10-03 added `GET /api/series/{series_id}/graph/visualization` → 50→51
operations, 37→38 templates, all three files updated together, tests green.

## Stub-client route tests in test_graph_api.py (no live Neo4j)

- `_viz_client()` defaults to ANONYMOUS, and anonymous readers are FIXED at order 1
  (PROB-04/#12) — a test asserting `effective_view_order == 2` will get 1 and fail.
  Use `_viz_client(user={"id": "user:test"}, progress=_ProgressRecord(2, 2))` to test
  higher boundaries (authenticated clamping matches the real resolver).
- Parametrized "all views" tests must gate per-view query params: `focus_id` is
  accepted ONLY for `graphrag_focus` (route returns 422 INVALID_REQUEST otherwise).
  Build `focus_ids = [...] if view == "graphrag_focus" else None` in the loop.
- The route test for the investigation view raises inside
  `project_investigation` (unresolved at session end) — served claims from
  `_FakeGraphService` must carry a `status` present in
  `_CLAIM_STATUS_DISPLAY_TIER` (canonical/corroborated/candidate) or the
  KeyError→ValueError path fires. Check the stub's served payload before assuming
  the projection is wrong. (Diagnosis note only — root cause not confirmed.)

## Cache tests without live Redis

- `test_visualization_cache.py` uses a `_FakeRedis` in-memory stand-in
  (dict[str, bytes], `get/setex/scan_iter/delete`) pointed at via
  `monkeypatch.setattr(graph_cache, "get_redis", lambda: fake)` plus
  `redis_url` forced to `"rediss://fake:6379"` — the documented 08-06 pattern.
  Reuse it for any new cache-dimension test; never require a live Redis.
- Always `unset PYTHONPATH` before `uv run pytest` on this repo.
