# Security audit 2026-08-15 — artifacts & P0 map (hdgrafcehennemi)

Full adversarial audit (10 subagents) completed 2026-08-15, commit 99eebd0.
Verdict: NOT public-ready until P0 lands (fixes planned as Phase 11, v1.4).

## Artifacts (repo root)

- `SECURITY_AUDIT.md` — full report: findings, attack chains A-H, P0-P3 roadmap.
- `SECURITY_ATTACK_SURFACE.md` — living 54-route table (method/auth/CSRF/rate/params).
- `SECURITY_TEST_PLAN.md` — regression tests mapped to findings (sections 1-3, 5, 8, 11 = phase-11 acceptance).
- `.planning/quick/20260814-security-audit/findings/S{1..10}-*.md` — per-agent evidence with file:line.
- `.planning/phases/11-security-hardening-audit-remediation-p0-p1/11-CONTEXT.md` — locked decisions D-01..D-12 for the fixes.

## P0 findings (fix targets — do not re-report as new discoveries)

- **SEC-BE-002** anonymous unclamped reads: candidates/notes/custom-nodes/custom-relationships/revisions GET accept any `visible_until_order` (notes/custom/revisions have NO persisted-episode check either). Chain A = full spoiler dump, zero privileges.
- **SEC-BE-001** fresh account (no progress record) bypasses boundary clamp on `/graph` + `/episodes` (graph.py:124-140 diverges from fail-closed `_resolve_effective_boundary` at graph.py:426-437).
- **SEC-BE-003/SEC-GR-004** `POST /candidates/ingest` (any auth'd user) persists client-chosen `visible_from_order` → spoiler/prompt-injection content visible to all + enters every user's LLM context; unthrottled (SEC-ADV-001), no cache invalidation (SEC-ADV-002).
- **SEC-BE-004/SEC-DOS-003** uvicorn without `--proxy-headers` → per-IP login limiter collapses to one site-global bucket (login lockout DoS).
- **SEC-DOS-001** rate limiter fail-open on Redis outage; **SEC-DOS-002** open-signup cost farm (~$600-860/day, 10 accounts).
- **SEC-LLM-001** BYOK `X-LLM-Base-URL` = authenticated SSRF primitive (scheme+host only validation, domain/settings.py:62-81).
- **SEC-DOS-004** no body-size limit; **SEC-INF-003** /docs public; **SEC-FE-001** no CSP on Vercel shell; **SEC-LOG-001** validation errors log raw inputs.

## Verified-strong (don't re-flag)

Spoiler boundary IS pre-retrieval (server-resolved boundary → Cypher param + `_visible_at` filter); all ~55 Cypher queries parameterized; NO LLM-generated Cypher; no HTTP/scraper tools in the 12-tool allowlist; citations validated against this-turn retrieved IDs; 48-byte hashed session tokens; CSRF Origin guard fail-closed; SSE framing-injection safe; no XSS sinks in frontend; no reachable dependency vulns (npm advisories all trace to shadcn CLI misdeclared as runtime dep — SEC-DEP-001); the "Redis password in git history" CRITICAL was REJECTED (literal `<token>` placeholder, byte-verified).

## Phase 11 locked decisions (short form)

D-01/02 single fail-closed boundary path (anonymous=1, no-record=1) on ALL reads + response shaping (no before/after/user_id for non-owners) · D-03 ingest: server-derived visibility + existence checks + rate limit + invalidate · D-04 trusted proxy · D-05 fail-closed limiter (env flag) · D-06 LLM cost controls (global semaphore, tool-call cap ≤8) · D-07 SSRF: ipaddress block of loopback/private/link-local/metadata in `_validate_base_url` · D-08 body limit 1MB + operations caps · D-09 docs_url=None in prod · D-10 vercel.json CSP headers + index.html meta · D-11 log sanitization (strip input/ctx) · D-12 P1: Max-Age, email_verified, TrustedHost, delimiter neutralization, cache-key focus bound, ops ≤20.

## GSD route notes

- Phase 11 lives at `.planning/phases/11-security-hardening-audit-remediation-p0-p1/`; ROADMAP header must stay top-level under `## Phases` (phase dirs for 1-10 were archived to `.planning/milestones/v1.3-phases/` — empty `.planning/phases/` makes `roadmap.analyze` report zero phases unless the ROADMAP.md header exists).
- After phase 11: refresh SECURITY_ATTACK_SURFACE.md route table + PROBLEMS.md ledger.
