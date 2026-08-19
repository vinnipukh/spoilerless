# Phase 11 Security-Hardening Planning — Plan-Set Authoring Notes

Session: 2026-08-15 — authored 8 PLAN.md files for `.planning/phases/11-security-hardening-audit-remediation-p0-p1/` (11-01..11-08). Reuse this for Phase 11 EXECUTION and for any future security/audit-remediation plan set.

## The `<code_snippets>`-after-`<action>` convention (MANDATORY for snippet-heavy plans)

The gsd-planner role template forbids fenced code blocks inside `<action>` ("Action is directive prose, not implementation code"). When the task requires exhaustive documentation with code snippets, do NOT inline ``` fences in `<action>`. Instead, after each `<action>` (still inside the `<task>`), add:

```xml
<action>Create X. Name signatures, imports, config keys, behavior — directive prose only.</action>
<code_snippets>
```python
# spoilerless/app/api/boundary.py — paste-ready, repo-grounded snippet
```
</code_snippets>
```

Rules that made the snippets executor-safe:
- Read the ACTUAL current code at the cited file:line BEFORE writing each snippet (audit line refs drift — verify). Import paths, helper names, and existing patterns must match the repo exactly (e.g. `_resolve_effective_boundary`, `derive_visible_from_order`, `_SECURITY_HEADERS`, `effective_view_order`, conftest `bootstrap_scratch_series`/`teardown_scratch_series`).
- Snippets must be complete enough to paste-and-adapt: full function bodies, route diffs, config Field definitions with defaults, test names + one-line asserts, exact pytest verify commands.
- Keep `verify` commands targeted: `uv run pytest spoilerless/tests/<file>::<new_test> -q -x` — never the full-suite runner (`scripts/run_phase10_backend_tests.py`) for plan tasks.

## Plan-set structure that worked (8 plans, 5 waves)

| Wave | Plans |
|---|---|
| 1 | 11-01 tracer (D-01 single fail-closed boundary path: new `spoilerless/app/api/boundary.py`, graph GET + candidates list/get, real tests) |
| 2 | 11-02 boundary expansion+shaping, 11-03 ingest hardening, 11-04 trusted proxy + fail-closed limiter |
| 3 | 11-05 LLM cost controls + SSRF |
| 4 | 11-06 body limit + docs-off + log sanitization, 11-08 P1 LLM/cache |
| 5 | 11-07 CSP shell + P1 auth + phase-end docs |

- Serialization driver: GSD file-ownership rule — `config.py`, `main.py`, `retrieval/pipeline.py` each touched by multiple plans ⇒ depends_on chains (11-04→11-05→11-06→11-07; 11-05→11-08). Single-plan waves are deliberate, not waste.
- Requirement coverage: every SEC-XX in ≥1 plan's `requirements` frontmatter; every D-NN cited in task bodies (decision-coverage gate reads both). Verified with a script at the end (grep D-NN per plan, SEC-XX per frontmatter, plus `fence-in-action` check).
- Estimate: `node C:/Users/arhan/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs query estimate-calibration` returned 0 samples ⇒ confidence `low`, tokens = raw (factor 1). Emit `{tokens, raw_tokens, tasks, confidence}`.
- `<threat_model>` mandatory per plan: trust boundaries + STRIDE register with sequential T-11-XX ids, severity/disposition, block on high per ASVS L1; T-11-SC row marked n/a when no package installs (this phase: stdlib `ipaddress`/`socket` only).

## Security-code map (verified file:line at 2026-08-15 HEAD — audit citations drift!)

- Shared async boundary resolver: `api/graph.py::_resolve_effective_boundary` **lines 397-457** (audit says 426-437). Pure formula: `spoiler/policy.py::resolve_effective_boundary` (115-155) + `effective_view_order` (100-112). Phase 11 moves the async wrapper to NEW `api/boundary.py`.
- Divergent clamps to delete: `api/graph.py::get_graph` 119-140, `api/series.py::list_episodes` 83-94.
- Candidates: `api/candidates.py::_require_resolved_boundary` 42-67; ingest route 121-142 (no rate limiter, no `invalidate_series` — approve/reject/edit DO invalidate at 248/280/320); `graph/candidates.py::INGEST_CANDIDATE_QUERY` 35-98, `_ingest_candidate_claims` 101-154 (persists client `visible_from_order` at param line 132; raw `str(exc)` error at 151), `list_candidate_claims` 292-337 (unbounded, ORDER BY created_at DESC).
- User content: `api/user_content.py` GETs at 51-77/126-129/177-180 (no auth dep, `Boundary = Annotated[int, Query(gt=0)]` at line 25); repo persisted-check `_require_persisted_boundary` 803-816 (uses `BOUNDARY_VALIDATION_QUERY` alias at line 429); note/list queries 392-414 (no user_id filter).
- Revisions: `api/revisions.py` list/get 44-97 (no persisted-episode check — SEC-ADV-003), `REVISION_LIST_QUERY` 20-33 returns before/after/user_id; revert f-string interpolation `revisions/__init__.py:280` (`CREATE (r:{resource_type} $props)`) and `:293` (`MATCH (target:{target_type} ...)`) — allowlist guard target (SEC-GR-014).
- Rate limiting: `services/rate_limit.py` — constants 33-38 (login 10/5min, chat 20/min, content-write 30/min), `rate_limit_identifier` 41-50 (`request.client.host`, user stamped by `require_current_user`), fail-open `__call__` 86-105, `init_rate_limiter` 116-148 (guarded on redis_url in `main.py:121-125`). Phase 11: fail-closed branch → `http_error(503, "rate_limit_unavailable", ...)` — lowercase code (envelope regex `^[a-z][a-z0-9_]*$`).
- SSRF: `domain/settings.py::_validate_base_url` 62-81 (scheme+host only today; `_ALLOWED_LLM_URL_SCHEMES` line 34; local vLLM/Ollama loopback documented as supported — Phase 11 rejects blocked hosts only when `environment == "production"`). BYOK path `services/chat.py::get_llm_provider` 114-146 already validates via `LLMSettingsUpdate(base_url=...)` at 126 — one validator, both paths.
- Config: `core/config.py` has NO `environment` field (Phase 11 adds it; docs-off and fail-closed limiter key on it). `allowed_emails` default "" (60-67), `frontend_origins` default localhost:5173 (56-59), `session_ttl_seconds` 604800 (35-38).
- Auth: `api/auth.py::_make_cookie` 69-78 (no max_age — add `max_age=settings.session_ttl_seconds`); `services/auth.py::AuthService.authenticate` 134-183 (reads sub/email/name/picture; `email_verified` check goes after `verify()` at 159, before allowlist 166 and role derivation 169).
- LLM pipeline: `retrieval/pipeline.py` tool loop 780-878 (`for call in new_calls:` 819 — cap site), `_finalize` 971-1102 (context assembly 986-997, citation validation 1053-1076), `ProposeChangesetInput.operations` 358-364 (add max_length=20). Delimiter formatters: `retrieval/context.py` ITEM_SECTION_FORMATTERS 71-78, CONTEXT_DELIMITERS 31.
- Cache: `cache/graph_cache.py` — `_cache_key` 71-72 (graph), viz key 155-167 (focus_sig dimension — SEC-DOS-005 cap target), `invalidate_series` 115-137 (epoch INCR + scan_iter DEL).
- CSP mirror source: `main.py::_SECURITY_HEADERS` 47-59 (CSP/HSTS/nosniff/XFO/Referrer-Policy; keep `https://accounts.google.com` in script-src). Shell: `frontend/vercel.json` (rewrites only today), `frontend/index.html` (no CSP meta).
- Body limit: `domain/change_set.py::ChangeSetCreateRequest.operations` line 263 (`min_length=1` only — add max_length=50).
- Tests: conftest has `bootstrap_scratch_series`/`teardown_scratch_series` (fresh driver/loop, scratch series + teardown, never series_dexter), autouse `_csrf_bypass_default` (FRONTEND_ORIGINS=* unless test_config), `NoopGoogleVerifier`. New Phase 11 test file: `spoilerless/tests/test_security_boundary.py` (module-scoped scratch series `series_scratch_boundary`).

## Locked decisions worth remembering (11-CONTEXT.md)

- D-01 single boundary path; D-02 shape before/after/user_id for non-owners; D-03 server-derive `visible_from_order` via `derive_visible_from_order(episode_order, current_progress=max(endpoint vfos))`, client mismatch ⇒ 422 consistently; D-04 render.yaml `--proxy-headers --forwarded-allow-ips` with documented placeholder CIDR + operator TODO (never `*`; dashboard untouched); D-05 fail-closed limiter (503), dev no-op on empty REDIS_URL, read caches still degrade; D-06 ipaddress-based SSRF validator (reject loopback/private/link-local/metadata v4+v6, decimal/hex literals, trailing dot, localhost; unresolvable ⇒ reject); D-07 global asyncio.Semaphore (default 4) + per-round tool cap ≤8 + open-signup startup warning (per-user daily token budget = consciously skipped, flag in SUMMARY); D-08 body cap 1 MB + operations max 50; D-09 docs off when ENVIRONMENT=production; D-10 CSP shell; D-11 log sanitization (drop input/ctx, no exc_info); D-12 Max-Age, email_verified, TrustedHost (FRONTEND_ORIGINS hosts + api domain), delimiter neutralization, viz focus cap 64/series, propose_changeset ≤20, revert label allowlist.

## Large-file write technique (essential for these plans)

`write_file` with very large markdown content truncated mid-generation twice. Working pattern: write part 1 ending with a unique marker comment (`<!-- PLAN_11_08_PART2 -->`), then `patch` (mode=replace) swapping the marker for the remainder. Verify at the end with grep that no markers survive.
