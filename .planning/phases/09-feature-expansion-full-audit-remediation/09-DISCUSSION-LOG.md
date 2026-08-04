# Phase 9: Feature Expansion & Full Audit Remediation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-05
**Phase:** 9-Feature Expansion & Full Audit Remediation
**Areas discussed:** Problem-remediation scope, Graph canvas strategy, Test isolation approach, Shareable link semantics, Export format, License

---

## Problem-remediation scope (PROB-01..21 vs all 57 findings)

| Option | Description | Selected |
|--------|-------------|----------|
| Baseline 45 | Keep REQUIREMENTS.md's PROB-01..21 mapping (#1–45); defer #46–57 to backlog | |
| All 57 | Fold #46–57 in as new PROB requirements (#46 landfill, #47 verifier tests, #48 notes-context, #49 visibility rules, #50 created_by, #51 revert link, #52 provider edges, #53 read-path nits, #55 env consolidation, #56 selector no-op, #57 graph hairball) | ✓ |

**User's choice:** "all lets go fast" (free text — full 57-finding scope, batch aggressively)
**Notes:** `docs/PROBLEMS.md` is the canonical ledger (57 findings as of 2026-08-05). REQUIREMENTS.md must be extended with PROB-22+ before planning. #54 is context-only (ChangeSet + spoiler read-path are the strongest code — do not rework).

---

## Graph canvas strategy (#57 + FEAT-11 filters)

| Option | Description | Selected |
|--------|-------------|----------|
| Lighter: filters + culling + focus | Keep cose-bilkent, add node/edge-type filter toggles, zoom label culling, focus/neighborhood mode, deterministic positions. Zero new deps | |
| Full: cluster-aware layout (fcose) | Swap to cytoscape-fcose with compound/cluster nodes from subplot tags; real separation at 132-claim density; new dependency + bigger GraphCanvas rework | ✓ |

**User's choice:** Full: cluster-aware layout (fcose)
**Notes:** Also ship FEAT-11 filter toggles, zoom culling, focus reducer over existing `faded`/`selected-dominant` classes, deterministic layout, edge bundling/opacity falloff. Fix `GraphCanvas.test.tsx:200` `toHaveLength(11)`. Prefer extracting from the god-file.

---

## Test isolation approach (PROBLEMS #15, PROB-06, 09-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Scratch-series + teardown (lighter) | Candidate/seed tests on scratch `series_*` ids + teardown fixtures (matches retrieval-test pattern); one-time zombie sweep; CI DB-pollution gate. No Docker dependency, works with AuraDB | ✓ |
| Testcontainers (heavy) | Docker containerized Neo4j per run; true isolation but heavy on Windows, doesn't test the real AuraDB target, CI already has a service container | |

**User's choice:** Scratch-series + teardown (lighter)
**Notes:** Never delete real dev user rows (ae8a41b7-db96-40e8-b6c2-2e3c69aedb11). Seed-idempotency assertions become state-independent.

---

## FEAT-09 shareable link semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Snapshot-at-creation | Token stores series_id + boundary + created_at; read-only route reuses the SAME spoiler-filter path; link always shows what was visible at creation | ✓ |
| Live-boundary link | Token references a live boundary that updates as the sharer advances; more useful but more spoiler risk | |

**User's choice:** Snapshot-at-creation
**Notes:** Revocation + 30-day expiry + stdlib `secrets` token = Claude's discretion (stated in CONTEXT D-10). New Neo4j label; unauthenticated-but-token-gated route; frontend read-only route distinct from the authenticated shell.

---

## FEAT-05 export format

| Option | Description | Selected |
|--------|-------------|----------|
| Markdown only | Zero new deps; backend renders visible knowledge as Markdown, FE downloads .md | ✓ |
| Markdown + PDF (jspdf) | Adds jspdf dependency; PDF nicer for sharing but heavier | |

**User's choice:** Markdown only

---

## LICENSE (PROB-10 / #28)

| Option | Description | Selected |
|--------|-------------|----------|
| MIT | Permissive, standard for public OSS, no copyleft obligations | ✓ |
| Apache-2.0 | Permissive + explicit patent grant; heavier | |

**User's choice:** MIT

---

## Claude's Discretion

- Exact fcose layout tuning, cluster tags, focus-reducer shape
- Share-token label name, expiry sweep mechanism
- FEAT-04 dashboard: augment existing dropdown (keep dropdown, add dashboard) unless evidence says replace
- FEAT-02 timeline placement: tabbed approach consistent with existing panel layout
- Which #46–57 items land in which plan wave; `ALLOWED_EMAILS` value for 09-03
- REBRAND-01 sequencing: rename EARLY in the phase so later feature plans touch renamed paths

## Deferred Ideas

- God-file decomposition of the 5 big modules (except #57 GraphCanvas extraction)
- Versioned Neo4j schema migrations (#19) — seed-as-schema continues
- Second demo series; Turkish UI strings; multi-region/HA, paid tier, mobile native
