---
phase: 01
slug: backend-graph-foundation
status: verified
threats_open: 0
asvs_level: 1
created: 2026-07-29
---

# Phase 01 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Browser/client → FastAPI | Untrusted series identifiers and episode visibility boundaries enter the API | User-controlled path and query parameters |
| FastAPI → Neo4j | Validated request data enters parameterized graph queries; database results return to response models | Graph identifiers, narrative facts, spoiler-sensitive metadata, provenance |
| Seed fixtures → Neo4j | Repository-controlled fixtures are ontology-validated before idempotent writes | Canonical graph data, visibility boundaries, evidence and source metadata |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-01-01 | Information Disclosure | Graph response | high | mitigate | `filter.py` applies `visible_from_order` in parameterized Cypher to nodes, edges, claims, sources, and evidence; full-response boundary sentinels pass | closed |
| T-01-02 | Information Disclosure | Relationship traversal | high | mitigate | Structural edge queries gate the relationship and both endpoints before serialization; graph closure is validated | closed |
| T-01-03 | Information Disclosure | Claim temporal validity | high | mitigate | Claim queries independently enforce `valid_from_order` and `valid_until_order`; dedicated validity test passes | closed |
| T-01-04 | Information Disclosure | API error responses | high | mitigate | Stable sanitized 404/422/503 contracts expose no raw Cypher, credentials, or driver details | closed |
| T-01-05 | Information Disclosure | Database authentication failures | high | mitigate | Centralized Neo4j exception handlers return safe fixed messages; unavailable-database test checks that secrets and `MATCH` are absent | closed |
| T-01-06 | Tampering | `visible_until_order` input | high | mitigate | ASCII integer parsing plus persisted episode-boundary lookup rejects missing, malformed, non-positive, and unknown orders with 422 | closed |
| T-01-07 | Information Disclosure | Unknown series lookup | medium | mitigate | Unknown `series_id` returns a stable 404 before graph disclosure | closed |
| T-01-08 | Injection | Neo4j query boundary | high | mitigate | User values are passed as `$series_id` and `$visible_until_order` parameters; no user input is interpolated into Cypher | closed |
| T-01-09 | Tampering | Seed ontology integrity | high | mitigate | Ontology version and all declared node, relationship, claim, status, and confidence allowlists are validated before writes | closed |
| T-01-10 | Tampering | Seed idempotency | medium | mitigate | Deterministic IDs and `MERGE`-based writes preserve exact node/relationship counts and snapshots across repeated setup runs | closed |
| T-01-11 | Information Disclosure | Missing visibility metadata | high | mitigate | Fixture validation requires integer `visible_from_order`; integration checks prove zero null visibility values; supported editions receive existence constraints | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-29 | 11 | 11 | 0 | Hermes Agent — ASVS Level 1 artifact and test verification |

Verification evidence:

- `uv run pytest backend/tests/test_graph_api.py backend/tests/test_seed_idempotency.py -q` → 13 passed.
- Live `/health` returned HTTP 200 with `database: connected`.
- Live order-1 graph response returned 11 nodes, 6 edges, 4 claims, 1 source, and 3 evidence fragments.
- Plan-time threat register was present in `01-PLAN.md`; ASVS Level 1 short-circuit applies because all registered threats are closed.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-29
