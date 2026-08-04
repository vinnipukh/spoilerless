---
phase: 07-spoiler-safety-hardening
plan: 4
subsystem: backend
tags: [spoiler-safety, visibility-gating, provenance, cypher-hardening]

# Dependency graph
requires:
  - phase: 07-02
    provides: policy service, effective-boundary plumbing
  - phase: 07-01
    provides: 07-AUDIT.md gap list (queries that lacked edge/endpoint gating)
provides:
  - spoiler/filter.py + retrieval/tools.py: every story-sensitive query constant now requires visible_from_order IS NOT NULL on edges AND endpoints (claim edges gated on the Claim too) — null-visibility relationship hidden with visible endpoints, satisfied relationship hidden with a hidden endpoint (VIS-03)
  - GRAPH_SUMMARY_COUNTS_QUERY hardened with OPTIONAL MATCH: an empty evidence/source subgraph previously dropped the entire counts row (latent bug found by the new scratch-series test); hidden relationships never influence count projections (D-16)
  - Provenance chain (VIS-04): future Evidence/Source never reach a visible Claim's context or responses; pipeline assemble_context gains defense-in-depth _visible_at boundary drop (D-03 fail-closed) applied to nodes/edges/claims/evidence/sources/notes
  - Notes queries boundary-gated (VIS-05) — USER_NOTES_QUERY non-null guards; note create/get/list already took the boundary param
affects: [07-05 search/counts, 07-07 chat context, 07-08 regression]

# Tech tracking
tech-stack:
  added: []
  changed: [backend/app/spoiler/filter.py, backend/app/retrieval/tools.py, backend/app/retrieval/pipeline.py, backend/tests/test_retrieval_tools.py, backend/tests/test_retrieval_pipeline.py]
  removed: []
  pinned: []

# Summary
Relationship and provenance visibility are now fail-closed at the query
level: no story-sensitive Cypher can select a row whose visible_from_order is
missing, and edges are gated independently of their endpoints. A new static
scan test locks this (every story-sensitive constant carries "visible_from_order
IS NOT NULL" + a boundary parameter), and live-DB tests prove null-vfo
relationships stay hidden with visible endpoints, satisfied relationships hide
when an endpoint is hidden, and hidden claims do not move count projections.
The GraphRAG context assembly got a second, independent boundary drop so a
record with missing/above-boundary visibility can never reach the provider
call even if a query upstream regressed. The counts-query OPTIONAL MATCH fix
was a genuine latent defect discovered by the scratch-series test.

# Tests
## New
- test_story_sensitive_query_constants_are_boundary_gated — static scan of 16 constants across both modules (>= 12 checked), asserts IS NOT NULL + boundary param
- test_null_visible_from_order_claim_relationship_hidden_with_visible_endpoints — live scratch chain, claim vfo set NULL -> get_claims omits it
- test_satisfied_claim_relationship_hidden_when_endpoint_hidden — endpoint vfo 99 -> claim omitted at boundary 3
- test_hidden_claims_do_not_change_graph_summary_counts — visible claim counted at boundary 3, hidden claim only at 99
- test_assemble_context_drops_above_boundary_or_missing_visibility_items — missing/99 items absent from rendered context at boundary 1
- Fixtures in test_retrieval_pipeline.py gained visible_from_order: 1 (D-03 missing-value drop requires it)

## Verification (canonical invocation)
unset PYTHONPATH && source .venv/Scripts/activate && pytest backend/tests/test_retrieval_tools.py backend/tests/test_retrieval_pipeline.py backend/tests/test_graph_api.py backend/tests/test_user_content_api.py backend/tests/test_change_set_api.py backend/tests/test_change_set_confirmation.py backend/tests/test_citations.py backend/tests/test_revisions.py backend/tests/test_openapi_contract.py backend/tests/test_frontend_contract_doc.py -q
=> 147 passed. Contract suites green (response shapes only; no route inventory change). Documented baseline failure set (test_seed_idempotency x3) unchanged.

# Status
Complete. Commit dde4080. Task 3 (notes) verified as already-gated (07-04 locks behavior via existing test_user_content_api hidden-matches-missing coverage + USER_NOTES_QUERY guards).
