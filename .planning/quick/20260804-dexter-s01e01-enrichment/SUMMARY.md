---
slug: dexter-s01e01-enrichment
status: incomplete
created: 2026-08-04
completed: 2026-08-04
reason_incomplete: live Neo4j Aura auth failed (invalid/expired credentials); DB seed, graph-API, GraphRAG, and browser acceptance could not be verified in this environment. Data + code + offline tests are complete and green.
---

# Summary — Dexter S01E01 source-grounded enrichment

## Done
- Source snapshot saved: `docs/sources/dexter/episode_101_fandom.txt` (one-time
  fetch of the Episode 101 Fandom page, provided by the user; excluded sections
  documented for provenance only).
- Enriched seed JSON (`data/dexter/seed/*` + `metadata/episodes.json`):
  - Characters 9 → 32 (23 new). Locations 4 → 24. Organizations 0 → 5.
    Objects 0 → 17. Events 3 → 39. Claims 9 → 105 (96 new). Evidence 9 → 36.
  - Corrected Harry Morgan `visible_from_order` 3 → 1 (Buddy flashback is Ep1).
  - Enriched Episode + Source (production code, airdate, synopsis, Fandom url,
    local snapshot path). Reused `dexter:source:s01e01` (no duplicate source).
- Extended `backend/app/graph/seed.py` to load/validate/upsert Organization +
  Object node files (were unsupported).
- Every new Claim has ≥1 EvidenceFragment; every Ep1 Evidence → the Ep1 Source.
- Unknown killer (`ice_truck_killer`) stays unidentified — no link to
  `rudy_cooper` or any civilian identity; all new story content vfo=1;
  Episode 2/3 records untouched.
- Tests: new `backend/tests/test_s01e01_enrichment.py` (47 offline
  integrity/required-content checks, **all green**). Updated
  `test_seed_idempotency.py` counts (265 nodes / 254 rels) and made
  `test_graph_api.py` boundary checks spoiler-safe + monotonic; image contract
  tolerates imageless enrichment characters.
- Offline `validate_seed` passes (ontology, referential, dup-id, provenance).

## Blocked (environment)
- Neo4j Aura rejects auth (`Neo.ClientError.Security.Unauthorized`). Could not
  seed the live DB or run the DB-backed tests (idempotency counts, graph-API
  boundaries, GraphRAG citations) or the browser manual acceptance.
- Once valid Aura credentials are in place:
  `pytest backend/tests/test_seed_idempotency.py backend/tests/test_graph_api.py`
  seeds + verifies; the app then renders the enriched Episode 1 graph.

## Node/edge totals (offline-computed, deterministic)
Nodes 265 — Character 32, Claim 105, Event 39, Evidence 36, Location 24,
Object 17, Organization 5, Episode 3, Source 3, Series 1.
Relationships 254 — PART_OF 3, PRECEDES 2, OCCURRED_IN 39, SUPPORTED_BY 105,
REFERS_TO 105.
