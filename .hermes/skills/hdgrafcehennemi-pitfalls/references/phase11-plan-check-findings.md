# Phase 11 Security-Hardening Plan-Check — findings & revision checklist (2026-08-15)

Plan-check verdict for the 8-plan Phase 11 set (`.planning/phases/11-security-hardening-audit-remediation-p0-p1`):
**REVISE.** 3/8 plans FAIL (11-01, 11-02, 11-05); 11-03/11-04/11-06/11-07/11-08 need smaller corrections.
Coverage was green everywhere else: all D-01..D-12 cited & implemented, all SEC-01..SEC-12 in frontmatter,
wave graph consistent (`wave = max(dep)+1`), all plans carry STRIDE threat models, no new deps / scratch-only
tests / targeted-pytest-only verifies / render.yaml dashboard invariant respected. 11-01 is a genuine tracer.

## Required corrections (revision mode)
1. **11-01 (BLOCKER)** — candidates omit→422 contract (PROB-05/#13) lost: Task 1 wires `effective` (never None)
   into `_require_resolved_boundary`, so absent `visible_until_order` → anonymous → 200, but Task 2 test 5 and the
   Task 1 snippet comment ("Omitted boundary still 422s") require 422. Fix: keep the explicit
   `visible_until_order is None → 422 INVALID_REQUEST` guard in list_candidates/get_candidate (candidates.py:48-54)
   before the resolver call.
2. **11-02 (BLOCKER)** — non-persisted-order 422 contradiction: Task 1 validates only the EFFECTIVE order
   ("anonymous callers can only ever validate order 1"), but Task 3's matrix test and locked SECURITY_TEST_PLAN 1.6
   demand 422 for anonymous `visible_until_order=99` on notes/custom/revisions (would be 200 under Task 1's wiring).
   NOTE: test plan 1.2 (anon 999→200) vs 1.6 (anon 99→422) are mutually unsatisfiable on a contiguous scratch
   series under any single order rule — the planner MUST make an explicit documented choice (e.g. requested-order
   validation for notes/custom/revisions while candidates clamp; or amend test-plan 1.6 with a [~] note).
   Also correct Task 2's claim "the resolver 422s on non-persisted orders" (it 422s only on a non-persisted EFFECTIVE).
3. **11-05 (BLOCKER)** — 5.3 redirect test cannot pass as specified: `OpenAICompatibleProvider.stream_chat` raises
   `LLMProviderUnavailable` only on `status_code >= 400`; a mocked **302** never raises it (pytest.raises fails),
   and `list(provider.stream_chat(...))` is a TypeError (async generator). Fix: assert `follow_redirects is False`
   + exactly one request + the 302 surfaced unfollowed (or mock a 500 and assert single request).
   Task 2 anchors wrong: the per-user slot is acquired in the api/chat.py ROUTE pre-check via public
   `acquire_generation_slot` — NOT inside ChatService.answer/answer_stream; and `answer()` (412) delegates to
   `answer_stream()` (278), so "acquire in both" double-acquires. Acquire the global semaphore ONCE in answer_stream.
4. **11-07** — `PROBLEMS.md` lives at **`docs/PROBLEMS.md`** (not repo root): fix Task 3 `<files>` and the verify
   `grep -n "11-" PROBLEMS.md`. Also verify greps `resolve_effective_boundary` in SECURITY_ATTACK_SURFACE.md but the
   mandated doc text is "shared resolver" — align token. Task 1 `<files>` includes test_frontend_contract_doc.py
   which is missing from files_modified frontmatter.
5. **11-03** — snippet bugs: `claim.candidate_id` does not exist on `ExtractionClaim` (id is deterministically
   derived — no candidate_id/claim_id field); `any(a, b)` is a TypeError (needs `any((a, b))`). Pagination: id-only
   cursor (`claim.id > $after_id`) is unsound under `ORDER BY created_at DESC, id ASC` — rows skipped/duplicated
   when created_at differs; composite `(created_at, id)` cursor needed. Move the §2.4 cache-invalidation test out of
   `test_security_boundary.py` → `test_candidate_ingest.py` to clear the wave-2 file collision with 11-02.
6. **11-04 (warning)** — fail-closed branch (a) `not settings.redis_url → return` is unconditional; production with
   empty REDIS_URL would silently run login/chat/write unthrottled. Gate the dev no-op on `environment != "production"`.
7. **11-06 (warning)** — caplog test `marker * 100` ≈ 2,400 chars < the 4,000 question cap → no validation error →
   422 never fires (route 404s on the unseeded series). Use ≥ 200× repetitions.

## Durable repo facts verified (spot-check anchors for future sessions)
- **PROBLEMS.md is at `docs/PROBLEMS.md`**; SECURITY_AUDIT.md / SECURITY_ATTACK_SURFACE.md / SECURITY_TEST_PLAN.md at repo root.
- **Boundary**: graph.py `_resolve_effective_boundary` at 397–457 (async, DB-aware; `(service, progress_service,
  series_id, user, requested_order=None, *, boundary_label)`); policy.py `resolve_effective_boundary` at 115 (pure).
  The resolver validates the EFFECTIVE order only — requested-order 422 contracts need per-route guards.
  Divergent clamps to delete: graph.py get_graph 124–140, series.py list_episodes 83–94.
- **Candidates**: `_require_resolved_boundary` candidates.py:42–67 (None→422 INVALID_REQUEST, non-persisted→422);
  list 154 / get 184 / ingest 121–142 (user + CSRF deps already present); `invalidate_series` at 248/280/320.
- **Chat slot**: `_acquire_generation_slot`/`_release_generation_slot` (chat.py:62–75) wrapped by public methods
  called from the api/chat.py streaming-route pre-check — not inside the service methods.
- **provider.py**: `__init__` 122–133 (httpx default follow_redirects=False); `stream_chat` is an async generator;
  error raise only on `status_code >= 400` (302 passes through, yields no events).
- **rate_limit.py**: identifier keys `user:{id}` or `ip:{request.client.host}` (never reads XFF); `__call__` 86–105;
  `init_rate_limiter` 116–148; `content_write_rate_limiter` 113; pre-existing 429 callback raises UPPERCASE
  "TOO_MANY_REQUESTS" (envelope-regex violation, out of locked scope).
- **main.py**: `_SECURITY_HEADERS` 47–59 is the CSP policy the vercel.json/index.html fix mirrors verbatim;
  FastAPI() 164–168; middleware section 191–219; lifespan 113–161 with `verify_google_client_id_equality` at 115.
- **errors.py**: `validation_handler` 231–237, `logger.error("validation_error", exc_info=exc)` at 234 (the raw-input
  leak SEC-LOG-001 fixes — exc_info must go, not just the input/ctx fields).
- **conftest.py**: autouse CSRF bypass (FRONTEND_ORIGINS=*) at 27–41, autouse RateLimiter.__call__ no-op at 142–160;
  `bootstrap_scratch_series` 69 / `teardown_scratch_series` 111. Enums: NoteTargetType {Character, Claim},
  CustomNodeType {Character, Event, Location, Organization, Object} in domain/user_content.py (revert label
  allowlist sources); `derive_visible_from_order(episode_order, current_progress)` at visibility.py:30.
- `test_security_boundary.py` is the shared boundary-regression file — 11-02 and 11-03 both claimed it in wave 2.

## Repeatable plan-check methodology (what caught these)
1. Grep EVERY file:line anchor (read_first/action/snippets) against the live repo — most were accurate; drift shows up fast.
2. Compare plan frontmatter `files_modified` vs per-task `<files>` (found the 11-07 omission).
3. Same-wave file-ownership scan across plans (found 11-02/11-03 collision).
4. Verify wave = max(dep)+1 AND semantic deps (11-08 mentions 11-06's ops cap but only depends on 11-05 — informational, OK).
5. Execute each snippet's logic against real code semantics: `any(a,b)` TypeError; 302 < 400; `list()` on async gen;
   marker×100 < 4000 cap; id-only cursor vs DESC ordering; "anonymous fixed at 1" vs "422 on non-persisted order".
6. Check the LOCKED acceptance tests (SECURITY_TEST_PLAN rows) against the plan's stated mechanism — internal
   contradictions (11-02 Task 1 vs Task 3) and test-plan self-contradictions (1.2 vs 1.6) are the highest-value findings.
