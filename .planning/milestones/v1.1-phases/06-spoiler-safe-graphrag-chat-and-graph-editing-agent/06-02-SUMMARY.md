---
phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent
plan: "02"
subsystem: graphrag
status: complete
tags: [graphrag, retrieval, tools, citations, prompt-injection, fastapi, neo4j, pytest]

requires:
  - phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent (plan 06-01)
    provides: single-tool retrieval layer (get_entity, get_neighborhood), tool-round pipeline, LLM provider layer, delimiter-wrapped context assembly
provides:
  - Full ten-tool retrieval allowlist (8 new tools beyond 06-01's two) with ontology-derived schemas and AppUser-safe execution
  - Leakage-matrix tests proving no tool leaks content beyond the persisted watch-progress boundary
  - Hardened pipeline: dedup, deterministic ordering, bounds (max_items/max_characters), tool-round cap behavior, no shadowed duplicate of assemble_context
  - CONTEXT_DELIMITERS updated to all 9 section tags; system prompt names them with data-not-instructions phrasing kept contiguous
  - Citation hardening with INSUFFICIENT_EVIDENCE_RESPONSE_TEMPLATE (test_citations.py)
---

# Plan 06-02 — Full Retrieval Toolset + Pipeline Hardening

**Status:** Complete — T1 RED `4418d09` / GREEN `5c3bff1`, T2 RED `9e1ba49` / GREEN `0ab6b4d`, T3 RED `7d8e428` / GREEN `c8c11c1`
**Duration:** ~45 min (2 executor attempts + orchestrator inline finish)

## Delivered

| Task | Description | Status |
|------|-------------|--------|
| T1 | 8 additional allowlisted retrieval tools + leakage-matrix tests | ✅ (29 passed) |
| T2 | Pipeline hardening: dedup, ordering, bounds, round limit; injection framing for every-section content | ✅ (58 passed incl. citations) |
| T3 | Citation hardening + `INSUFFICIENT_EVIDENCE_RESPONSE_TEMPLATE` | ✅ |

## Verification (exact commands + results)

- `uv run pytest tests/test_retrieval_tools.py -x` → **29 passed** (T1 GREEN)
- `uv run pytest tests/test_retrieval_pipeline.py tests/test_prompt_injection.py tests/test_retrieval_tools.py -q` → green after T2 hardening
- `uv run pytest tests/test_citations.py tests/test_retrieval_pipeline.py tests/test_retrieval_tools.py tests/test_prompt_injection.py -q` → **58 passed** (T3 GREEN)
- Full suite: **249 passed**; 5 failed + 7 errors all pre-existing Phase-5 debt (`test_candidate_*.py` missing `data/dexter/test/extraction_fixture.json`, `test_extraction_models.py` same fixture, `test_seed_idempotency.py` drifted DB seed counts) — no new failures

## Key Decisions

- Root cause of the 16 T2 failures: the partial hardening left a DUPLICATE `assemble_context` — the old definition shadowed the new hardened one (later def wins in Python). Deleted the old one.
- `system_prompt.py` `CONTEXT_DELIMITERS` synchronized 1:1 with pipeline `CONTEXT_SECTIONS` (all 9 tags); prompt phrases asserted by tests kept contiguous (no line-wrap drift).
- Citation hardening: insufficient evidence → `INSUFFICIENT_EVIDENCE_RESPONSE_TEMPLATE` rather than passing a weakly-grounded answer.

## Issues Encountered

- Subagent iteration caps (50 tool calls) hit twice mid-plan; continuation executor + orchestrator inline commit finished T3 GREEN.

## Key Files

- created: `backend/tests/test_citations.py`
- modified: `backend/app/retrieval/tools.py`, `backend/app/retrieval/pipeline.py`, `backend/app/llm/system_prompt.py`, `backend/tests/test_retrieval_tools.py`, `backend/tests/test_retrieval_pipeline.py`, `backend/tests/test_prompt_injection.py`
