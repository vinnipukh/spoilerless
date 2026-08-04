---
slug: dexter-s01e01-enrichment
status: in-progress
created: 2026-08-04
mode: quick --full --research
---

# Quick Task: Dexter S01E01 source-grounded graph enrichment

Source-grounded correction + major enrichment of the Dexter Season 1 Episode 1
knowledge graph, using ONLY the Episode 101 Fandom page (snapshot at
`docs/sources/dexter/episode_101_fandom.txt`).

## Ground rules (from task brief)
- All new story content: `visible_from_order = 1` (safe right after watching Ep1).
- Bloodless-body killer stays UNIDENTIFIED (no civilian identity / alias / family
  / later-season link). Do NOT touch `rudy_cooper` (vfo=3, later reveal).
- Reuse existing nodes; no duplicate canonical nodes; no second Ep1 graph.
- Do not modify Episode 2/3 data, auth, ChangeSets, frontend, DB engine.
- Interpretive facts → origin/status candidate, confidence medium.
- Ontology is fixed (no new predicates): DATING→KNOWS, SUPERVISES→WORKS_WITH.
- Every automatic Claim needs ≥1 EvidenceFragment; every Evidence → the Ep1 Source.

## Architecture facts (audit)
- Seed is JSON-driven: `data/dexter/metadata/{series,episodes}.json`,
  `data/dexter/seed/{characters,events,locations,claims,sources,evidence_fragments}.json`.
- Relationships are modelled AS Claims (subject_id, predicate, object_id + provenance).
  Both claim endpoints MUST be seeded nodes (validate_seed enforces).
- ID convention: `dexter:<type>:<slug>`; claims `dexter:claim:s01e01:<slug>`.
- Idempotent upsert via MERGE on id. `validate_seed` runs offline (no DB needed).
- DB is Neo4j Aura (cloud); tests in `backend/tests` use `.venv`.

## Corrections to earlier assumptions
- Harry Morgan was `visible_from_order=3`; Ep1 has the Buddy flashback → set to 1.
- Reuse existing Ep1 Source `dexter:source:s01e01` (enrich with Fandom url +
  snapshot path) instead of minting a second `source_dexter_fandom_episode_101`.

## Steps
1. [x] Save source snapshot.
2. [ ] Author enriched JSON via generator (chars, events, locations, orgs, objects,
   claims+evidence). Event-centric to avoid a Dexter-star graph.
3. [ ] Validate offline against ontology (referential + dup-id + provenance).
4. [ ] Add integrity + required-content tests (runnable on JSON).
5. [ ] Run test suite (offline subset always; live-DB subset if Aura reachable).
6. [ ] Report; decide commit-safety.
