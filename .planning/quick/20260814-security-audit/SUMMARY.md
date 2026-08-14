---
status: complete
date: 2026-08-15
---

# Quick Task SUMMARY — 20260814-security-audit

**Description:** Full adversarial security audit (10-subagent) of the Spoilerless app — frontend, backend/API, LLM/GraphRAG, Neo4j, Redis, auth, deployment, dependencies, abuse/DoS, privacy/logging.

## What was done

- Dispatched 10 specialized audit subagents (S1 architecture/attack-surface mapper; S2 backend/API; S3 frontend; S4 LLM red team; S5 Neo4j/graph; S6 secrets/infra; S7 dependencies; S8 abuse/DoS; S9 privacy/logging; S10 independent adversarial reviewer). All static analysis + safe local verification; no live-DB writes, no prod traffic, no secrets printed.
- Per-agent findings: `.planning/quick/20260814-security-audit/findings/S{1..10}-*.md` (+ S0 lead notes). ~90 unique findings after dedup + S10 adjudication: 1 CRITICAL (config-dependent cost farm), 14 HIGH, 27 MEDIUM, 28 LOW, ~20 informational/verified-positive.
- Deliverables (repo root):
  - `SECURITY_AUDIT.md` — exec summary, architecture, trust boundaries, entry-point inventory, LLM capability map, confirmed findings, attack chains A–H, per-domain analyses, P0–P3 remediation roadmap.
  - `SECURITY_ATTACK_SURFACE.md` — living 54-route endpoint doc (auth/CSRF/rate/params per route).
  - `SECURITY_TEST_PLAN.md` — 11 sections of regression tests mapped to findings, CI-ready markers.

## Headline results

- **Spoiler boundary (the app's core guarantee) is broken anonymously and certainly**: unauthenticated, unthrottled reads (candidates/notes/custom-nodes/custom-relationships/revisions) accept any client-chosen `visible_until_order`; fresh accounts (no progress record) bypass the clamp on `/graph` + `/episodes` (SEC-BE-001/002, SEC-GR-005/006/007).
- **One-request graph poisoning**: any authenticated user ingests spoiler/prompt-injection content at `visible_from_order=1`, visible to all + enters every user's LLM context (SEC-BE-003/SEC-GR-004); ingest is unthrottled (SEC-ADV-001).
- **Availability/wallet**: login rate limit collapses into one site-global bucket behind Render's proxy (SEC-BE-004); limiter fail-open (SEC-DOS-001); open-signup cost farm ≈ $600–860/day with 10 accounts (SEC-DOS-002).
- **Adjudication corrections**: S10 rejected the audit's only CRITICAL (SEC-INF-001 — Upstash credential in README/history is literal placeholder `<token>`, verified byte-wise); downgraded SEC-FE-006 (visitor flag forgeable but server-side auth holds); upgraded SEC-BE-004 availability impact to HIGH; 4 new findings (SEC-ADV-001..004).
- **Strong core verified**: parameterized Cypher everywhere, no LLM-generated Cypher, pre-retrieval boundary enforcement, citation validation, hashed session tokens, CSRF origin guard, allowlist logging, no XSS sinks, no reachable dependency vulns.
- **FINAL VERDICT (S10): NOT public-ready** — 10-item P0 list must land first (see SECURITY_AUDIT.md § Remediation Roadmap).

## Files

- `.planning/quick/20260814-security-audit/PLAN.md`
- `.planning/quick/20260814-security-audit/findings/S0-lead-notes.md`, `S1-architecture.md` … `S10-adversarial.md`
- `SECURITY_AUDIT.md`, `SECURITY_ATTACK_SURFACE.md`, `SECURITY_TEST_PLAN.md` (repo root)

## Next steps (operator)

1. Review P0 list; decide which fixes land before public exposure.
2. Verify prod env: `ALLOWED_EMAILS`, `ADMIN_EMAILS`, `FRONTEND_ORIGINS`, `REDIS_URL`, `LLM_ENABLED` (dashboard-only values — unverifiable from repo).
3. Implement regression tests from SECURITY_TEST_PLAN.md §1–3 first.
