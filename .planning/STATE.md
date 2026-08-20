---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Security Hardening (audit remediation P0/P1)
status: Phase 11 complete — awaiting next milestone
stopped_at: Completed 11-08-PLAN.md
last_updated: "2026-08-20T15:30:00.000Z"
last_activity: 2026-08-20
last_activity_desc: Phase 11 Security Hardening (8/8 plans) verified and shipped
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 45
  completed_plans: 45
  percent: 100
current_phase: 11
current_phase_name: security-hardening-audit-remediation-p0-p1
---

# HD Graf Cehennemi — Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-20 after v1.4)

**Core value:** Users can safely explore a TV-series knowledge graph — and chat about it — without ever seeing information beyond their selected watch progress; the backend filters before data reaches the frontend, the LLM, or any tool call. One shared fail-closed boundary resolver (`resolve_effective_boundary`) is the single enforcement seam.
**Current focus:** Phase 11 shipped (2026-08-20) — all P0/P1 audit findings closed; awaiting next milestone

## Current Position

Phase: 11 Security Hardening complete (8/8 plans, verification passed)
Plan: 11-08 (last plan in phase)
Status: Phase 11 complete — awaiting next milestone
Last activity: 2026-08-20 — Phase 11 Security Hardening (8/8 plans) verified and shipped

## Performance Metrics

**Velocity:**

- Total plans completed (all milestones to date): 51 (v1.0/v1.1: 27, v1.2: 8, v1.3: 37 (8+18+11), v1.4: 8 — Phase 11)
- v1.3: 37 plans completed (08:8, 09:18, 10:11) — all verified (08 VERIFICATION.md, 09 40/42 must_haves, 10 11/11)
- v1.4: 8 plans completed (11-01..11-08) — security hardening P0/P1, verified 2026-08-20 (8/8 must_haves, 12/12 SEC requirements)

**By Phase:**

| Phase | Plans | Notes |
|-------|-------|-------|
| 1–6 (v1.0/v1.1) | 27 | See `.planning/milestones/v1.1-ROADMAP.md` for per-plan durations |
| 7 (v1.2 Spoiler-Safety Hardening) | 8 | See `.planning/milestones/v1.2-phases/07-spoiler-safety-hardening/` SUMMARY.md files |
| 8 (v1.3 Production Deployment) | 8 | Phase complete — VERIFICATION.md passed 2026-08-05 |
| 9 (v1.3 Feature Expansion) | 18 | Phase complete — VERIFICATION.md passed 2026-08-13 (40/42 must_haves) |
| 10 (v1.3 Polish) | 11 | Phase complete — VERIFICATION.md passed 2026-08-14 (11/11) |
| 11 (v1.4 Security Hardening) | 8 | Phase complete — VERIFICATION.md passed 2026-08-20 (8/8 must_haves, 12/12 SEC requirements) |

**Recent Trend:** v1.4 — Phase 11 (Security Hardening P0/P1) complete and verified 2026-08-20; all P0/P1 audit findings closed; awaiting next milestone.

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 10 P02 | 43min | 2 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table. Recent decisions affecting current work:

- [PROJECT.md]: Global (non-per-user) LLM Settings, built without a threat model — flagged as SSRF/cross-user-takeover surface; full fix deferred to v1.3 (Phase 8, AUTH-04/AI-01..03)
- [08-02]: LLM settings moved to browser-only BYOK — frontend keeps key/base_url/model in localStorage ('hdgraf:byok-llm-settings') and sends them per-request as X-LLM-* headers; frontend api/settings.ts (GET/PUT /api/settings/llm) removed. Backend endpoint stays for now; 08-03 gates it to admin or retires it.
- [08-03]: Admin role derived server-side from ADMIN_EMAILS at every login and persisted on AppUser (re-synced on each login — removals demote on next sign-in); require_admin gates candidate approve/reject/edit, ChangeSet confirm, and GET/PUT /api/settings/llm (403 "forbidden"). /api/settings/llm survives as admin-only server fallback (BYOK covers per-user path). ChangeSet reject/revert and candidate ingest/list/get intentionally NOT gated (Phase 9/PROB-01 scope).
- [08-05]: Rate limiting is Redis-backed via pyrate-limiter's atomic RedisBucket (Lua script) shared across Render workers (D-14). fastapi-limiter 0.2.0 is the pyrate-limiter rewrite — no FastAPILimiter.init (RESEARCH A5 verified live); kept its identifier+callback dependency contract in services/rate_limit.py with per-window RateLimiter(times, seconds) instances (login 10/5min per IP; chat-send 20/min per user; content-write 30/min per user-or-IP), init_rate_limiter() bound at startup from main.py lifespan guarded on redis_url (empty ⇒ disabled). require_current_user now stamps request.state.user so identifiers key per-user. Tests never touch Redis: conftest autouse fixture no-ops RateLimiter.__call__.
- [v1.3 requirements]: Stack additions locked for this milestone only — Upstash Redis (caching) and a hosted target (Vercel/Render/AuraDB); no other new stack components (no second graph DB, no JWT auth, no frontend rewrite)
- [v1.3 roadmap]: AUTH-01 (email allowlist) and AUTH-02 (`/api/auth/dev` removal) landed ahead of formal planning; mapped to Phase 8 for traceability as verification/regression work, not new build work
- [v1.3 roadmap]: Phases sequenced access-control/security (8) → data+hosting infra migration (9) → CI/monitoring/docs (10), since exposing the app publicly (Phase 9) should follow session/CORS/rate-limit hardening (Phase 8), and monitoring/docs (Phase 10) need a real deployed target to point at
- [09-02]: #42 NameError was LIVE (plan premise wrong) — fixed in a36676a; verifier + progress regression nets red-capable
- [10-01]: Episode Overview production default = Variant A (characters + major Events) at projection_version 1.0.0, from measured fixed-data evidence (13 nodes inside 12–28 target on cumulative S01E02 vs B's 11; edges 4/7, crossings 0, stability 1.0, procedural labels 0 for both). Decision log: docs/decision-logs/phase-10-visualization.md. Full Graph stays Advanced (D-11).
- [10-02]: Episode Overview projection implements the recorded 10-01 Variant A decision (characters + major Events) at projection_version 1.0.0; display_tier derives from safe editorial event tier (major=1, supporting=2, micro=3; characters=1; containers=2) pending the 10-03 display_tier source audit.
- [10-02]: Boundary enforcement centralized in policy.resolve_effective_boundary: one pure D-05 resolver for graph/projection/expansion/path/search/focus/restoration inputs; missing progress fails closed to order 1; the projection service rejects hidden rows before projection (T10-LEAK-02/T10-BOUND-02).
- [10-02]: Neutral DTO carries projection_version + effective_view_order metadata as the T10-CACHE-02 cache contract; no cache introduced in 10-02.
- [10-02]: Human edge classes (family/work/knows/precedes/part_of/...) replace raw Neo4j relation names in normal DTOs; unmapped relationship types fail closed (D-14).
- [11-01/11-02]: Single fail-closed boundary resolver `spoilerless/app/api/boundary.py::resolve_effective_boundary` gates every spoiler-sensitive read (graph, candidates, notes, custom nodes/relationships, revisions, episodes, visualization, expand, path, export); anonymous/no-record →1, non-persisted `visible_until_order` 422, non-owner shaping drops `before/after/user_id`.
- [11-03]: Ingest hardening — `visible_from_order` server-derived via `derive_visible_from_order`, subject/object/episode existence validated, rate-limited (`content_write_rate_limiter`) + `invalidate_series`, pagination `limit 1..500` with cursor `after_created_at/after_id`.
- [11-04]: Trusted proxy + fail-closed rate limiting — `render.yaml --proxy-headers --forwarded-allow-ips "<RENDER_PROXY_CIDRS>"` restores per-IP keys, XFF spoof-proof; `RateLimiter` fails closed (503 `rate_limit_unavailable`) when Redis unavailable in production, dev keeps no-op, `request.client` None → `ip:unknown` (BUG-BE-02).
- [11-05]: SSRF hardening (`ipaddress` block loopback/private/link-local/metadata, decimal/hex, trailing-dot, localhost) on both BYOK and stored `base_url`, gated on `environment==production`; LLM cost caps via global `asyncio.Semaphore(4)` + per-round tool cap 8 (`llm_max_tool_calls_per_round`) + `warn_if_open_signup` in production.
- [11-06]: Body-size bound (1 MB 413 `payload_too_large` via pure-ASGI middleware for Content-Length + chunked), docs off (`docs_url=None` when `ENVIRONMENT=production`), capped ChangeSet ops at 50, admin-gated `POST /change-sets/{id}/revert` (SEC-AUTH-02), sanitized validation logs (no `input`/`ctx`).
- [11-07]: CSP/HSTS shell (`frontend/vercel.json` headers + `frontend/index.html` meta, Google allowed), session `Max-Age=session_ttl_seconds`, `email_verified is not True` reject, `TrustedHostMiddleware` from `FRONTEND_ORIGINS`, plus BUG-FE-01 series hydration + BUG-FE-02 bodyless Content-Type cleanup + QUAL-01 verification script portability.
- [11-08]: Delimiter neutralization (`_neutralize` on context lines + `_neutralize_answer_delimiters` on answers), bounded viz cache `FOCUS_SET_CAP=64` per series, `propose_changeset` ops ≤20, revert `_REVERT_LABEL_ALLOWLIST` + fail-closed ownership (`None` requires admin), extracted `ChangeSetService.propose_via_tool` (QUAL-02).

### Pending Todos

None yet.

### Blockers/Concerns

- Pre-existing test-pollution debt in `test_seed_idempotency.py` (untorn-down candidate-origin fixture from `test_candidate_ingest.py`; 8 candidate nodes currently in the shared live DB) — now mapped to Phase 9 carry-over **09-05** (PROB-06)
- Pre-existing frontend lint debt (28 errors, none newly introduced in v1.1) — now mapped to Phase 9 carry-over **09-06** (PROB-08; CI fix branch `ci-smoke-test` scoped 3 React-Compiler-era rules to warnings, 0 lint errors verified locally)
- Deploy-time: REDIS_URL (Upstash rediss:// from 08-01 user_setup) must be set on Render for rate limiting to activate; empty = rate limiting disabled (by design, 08-05) — mapped to Phase 9 carry-over **09-04**

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260805-te3 | Visitor (misafir) read-only login — browse the graph, no node/note writes (backend anon writes already 401; fixed DetailPanel TooltipProvider crash) | 2026-08-05 | 73b87a7 | [260805-te3-add-a-visitor-misafir-read-only-login-vi](./quick/260805-te3-add-a-visitor-misafir-read-only-login-vi/) |
| 260810-testtime | Backend test suite 75m -> ~40m serial: DRY conftest helpers (seed_live_database, module_cleanup_fixture, run_query/helper_db/run_async), per-test cleanup -> module-scoped, chat_persistence async'd, pytest-asyncio loop_scope=module, ghost-node fixed-id cleanup fix. Parallel chunks on AuraDB measured SLOWER (connection contention); <8m needs local docker Neo4j. Pre-existing reds: 3 doc-contract + 1 seed-image | 2026-08-10 | a56b52f | — |
| 260810-ep1box | Episode-band cluster box is a non-interactive dashed outline — transparent fill (dot-grid shows through), dashed border, events:no (cluster taps no longer open a bogus DetailPanel) | 2026-08-10 | c77874d | — |
| 260811-prob09 | PROBLEMS.md NINTH-PASS fixes: #58 pipeline ProgressService imports; #59 path-route boundary resolves from persisted progress (never MAX_PATH_HOPS); #75 BacklinksTab jump-to-node + fresh hover card; #76 onRefreshGraph to GraphCanvas (non-destructive custom-node refresh); #80 dead-code sweep (10 items; 3 of the finding's claims verified FALSE at HEAD) | 2026-08-11 | 3d6dc33 | — |
| 260812-gra | Refresh graph automatically on website open: run the same forced Cytoscape layout and fit used by Refresh graph when the live canvas instance is created | 2026-08-12 | f968788 | [260812-gra-refresh-graph-on-open](./quick/260812-gra-refresh-graph-on-open/) |
| 260813-ftl | Hide note-adding UI (Add Note / NoteEditor / NoteItem edit-delete) and revision History tab from visitor (misafir) mode; readOnly threaded into DetailPanel from App.tsx | 2026-08-13 | ed24814 | [260813-ftl-hide-note-adding-ui-buttons-and-revision](./quick/260813-ftl-hide-note-adding-ui-buttons-and-revision/) |
| 260813-gao | Fix broken node portrait images in production: apiUrl() helper prefixes relative image_url with VITE_API_BASE_URL at both consumption sites (Cytoscape imageUrl + DetailPanel img src); local vite-proxy behavior unchanged | 2026-08-13 | 73ed961 | [260813-gao-fix-broken-node-portrait-images-in-produ](./quick/260813-gao-fix-broken-node-portrait-images-in-produ/) |
| 260813-wyp | Resizable Story Event Timeline rail: drag its left edge leftwards to widen (pointer events, 240..min(640,60vw) clamp) or use ArrowLeft/ArrowRight on the focused separator handle (±16px); no new dependencies | 2026-08-13 | b714e79, 316b938 | [260813-wyp-make-the-story-event-timeline-rail-horiz](./quick/260813-wyp-make-the-story-event-timeline-rail-horiz/) |
| 260813-fil | Graph Filters panel restyled to the Settings language: card header with All/None ghost actions, Separator sections, labeled rows with role=switch toggles (44px rows, focus rings); new GraphFilterPanel.test.tsx (5 tests) | 2026-08-13 | 98c5270 | — |
| 260814-viz | Phase-10 visualization frontend wiring (milestone-audit GAP-1 closure): Characters/Evidence tabs fetch character_network/investigation projections, Expand menu (7 keys) → /graph/expand with delta merge + Undo/Collapse, Answer Graph fetches graphrag_focus with citation focus ids; GraphCanvas visualization prop: undefined=leave-projection, null=loading-retain; Story/Advanced keep legacy scene (user content) | 2026-08-14 | b133ee7, ec13d3d | — |

## Deferred Items

Items acknowledged and carried forward, not in v1.3 scope:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| quick_task | dexter-s01e01-enrichment (20260804) — data/code/offline tests (47) green; live AuraDB seed + DB-backed tests + browser acceptance unverified (Aura auth failure at the time) | Incomplete | Acknowledged at v1.3 close 2026-08-14 (milestone audit §4.1) |
| quick_task | 20260814-security-audit — 10-subagent adversarial audit; deliverables SECURITY_AUDIT.md / SECURITY_ATTACK_SURFACE.md / SECURITY_TEST_PLAN.md; verdict NOT public-ready (spoiler-boundary bypass anonymous + certain; 10-item P0 list) | Complete | 2026-08-15 |
| OPS | Full CI/CD: dependency scanning, artifact publication, staged promotion, branch-protection enforcement (OPS-01 is a minimal PR gate only) | Deferred | v1.3 requirements gathering |
| OPS | Full observability: centralized logs, metrics dashboards, incident/rollback runbook automation (OPS-02 is a single health-check ping only) | Deferred | v1.3 requirements gathering |
| Content | Person / ACTED_AS / APPEARS_IN actor model | Deferred | Carried from v1.1/v1.2 |
| Content | Reviews, ratings, trivia, recommendations | Deferred | Carried from v1.1/v1.2 |
| Ingestion | Automated ingestion/extraction from external sources (OpenSubtitles, scripts, Fandom/IMDb/news) | Deferred | Carried from v1.1/v1.2 |
| Hosting | Multi-region/HA hosting, paid tier / usage-based billing | Out of scope | v1.3 requirements gathering |

## Session Continuity

Last session: 2026-08-20T15:30:00.000Z
Stopped at: Completed 11-08-PLAN.md (Phase 11 verified)
Resume file: None

## Operator Next Steps

- Awaiting next milestone definition via /gsd-new-milestone — Phase 11 (v1.4) shipped; no open high-severity audit findings remain
