---
phase: 07-spoiler-safety-hardening
plan: 5
subsystem: backend
tags: [spoiler-safety, search, counts, response-shape]

# Dependency graph
requires:
  - phase: 07-04
    provides: relationship/provenance gating, OPTIONAL MATCH counts fix
provides:
  - SEARCH_ENTITIES_QUERY hardening: alias/entity gating — hidden entities behave like nonexistent in search/autocomplete (SEARCH-01, D-15); regression tests for alias + entity fuzzy matches
  - GRAPH_SUMMARY_COUNTS_QUERY endpoint gating: counts aggregate only resources fully visible at the boundary — a claim whose endpoint node is hidden is excluded (SEARCH-02, D-16)
  - Summary response carries only visible counts: no total/last_appearance/dead/alive signals (json-serialized scan test)
  - Response-shape sweep test: GraphResponse/EpisodeResponse serialized at boundary 1 contain no future-title, hidden-count, or life-status keys; future episodes expose only the D-08 generic display_title with is_unlocked false
  - graphElements.ts D-16 layout rule comment: node styling consumes only backend-filtered GraphResponse fields
affects: [07-07 chat context, 07-08 regression]

# Tech tracking
tech-stack:
  added: []
  changed: [backend/app/retrieval/tools.py, backend/tests/test_retrieval_tools.py, backend/tests/test_graph_api.py, frontend/src/components/graph/graphElements.ts]
  removed: []
  pinned: []

# Summary
The search/autocomplete surface and every count projection now leak nothing
about future content: search_entities gates hidden entities/aliases to
nonexistent (D-15), and the graph summary counts claims only when the claim
AND both endpoint nodes are fully visible at the boundary (D-16), with the
response shape carrying no totals, last-appearance, or life-status signal.
A serialization-level sweep locks the absence at the key level for boundary-1
GraphResponse/EpisodeResponse payloads, and the frontend layout code documents
the rule that styling derives only from backend-filtered data. No
Person/ACTED_AS/APPEARS_IN model introduced (D-17 — deferred-design only).

# Tests
## New
- test_retrieval_tools.py: search alias/entity leak regressions (committed 596eaa3); test_graph_summary_counts_never_expose_total_future_or_last_appearance; test_graph_summary_counts_exclude_claims_with_hidden_endpoints (committed 5138497)
- test_graph_api.py::test_boundary_one_responses_carry_no_future_signals — key-level absence sweep for graph + episodes at boundary 1 (committed f136d42)

## Verification (canonical invocation)
unset PYTHONPATH && source .venv/Scripts/activate && pytest backend/tests/test_retrieval_tools.py backend/tests/test_graph_api.py backend/tests/test_retrieval_pipeline.py backend/tests/test_openapi_contract.py backend/tests/test_frontend_contract_doc.py backend/tests/test_citations.py backend/tests/test_user_content_api.py backend/tests/test_change_set_api.py -q
=> 85 passed (+ contract/user-content/change-set suites 61 passed in the Task-3 gate). Baseline failure set unchanged. ACTED_AS/APPEARS_IN grep: 0 matches.

# Status
Complete. Commits: 596eaa3 + c70027d (Task 1, executor), 5138497 (Task 2 counts, orchestrated completion after executor 429 death — repaired two mid-edit test breakages), f136d42 (Task 3 sweep + layout comment). 07-05-SUMMARY written by orchestrator.
