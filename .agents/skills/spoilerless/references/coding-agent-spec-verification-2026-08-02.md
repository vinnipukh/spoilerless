# Coding-agent specification verification (2026-08-02)

Use this when adversarially checking `HD_GRAF_CEHENNEMI_CODING_AGENT_SPEC_V2.md` against the live repository.

## Durable verification approach

- Treat the spec as a mixed document: current-state claims, architectural invariants, examples, recommendations, and future intent coexist.
- Do **not** fail future requirements merely because they are not implemented. Fail them when the document classifies an already-implemented capability as future-only, or when current code implements the opposite of a stated invariant.
- Verify beyond literal backtick paths: inspect actual route prefixes/decorators, Pydantic enums/models, seed data, Cypher visibility clauses, frontend sheet placement/links, and executable module entry points.
- For commands, verify that the target module has an executable `main`/`__main__` path; module existence alone is insufficient. Here, `python -m app.graph.seed` imports definitions but does not seed. The executable implementation is `backend.app.graph.setup:main`.
- Current origin vocabulary is `canonical | candidate | user`, not the old spec's `curated | automatic | user`. Check backend `Origin`, seed JSON, candidate ingestion, and frontend wire comments together.
- A route having an optional spoiler-boundary parameter is not backend-enforced filtering. Candidate list/get routes must be checked specifically for mandatory progress/boundary enforcement.
- Frontend behavior claims require component-level evidence: `DetailPanel` is left-sided; `ChatSheet` is right-sided; evidence source locators are currently plain text rather than links.

## Artifact verification

The verifier output is the only allowed write for a read-only audit. Validate:

1. JSON parses.
2. `claims_checked == claims_passed + claims_failed`.
3. `claims_failed == len(failures)`.
4. Every failure has exactly `line`, `claim`, `expected`, and `actual`.
5. Run a targeted read-only contract test when route evidence is central (`backend/tests/test_openapi_contract.py`), not the live-Neo4j full suite.

## Fix-iteration final reverification

After the eight corrections landed in the working specification, independently re-extract and re-check the live spec/code before reading any prior report; use the prior JSON only as a count/comparison aid. The final fresh ledger was **91/91 claims passed, 0 failures** and was written to `.planning/tmp/verify-HD_GRAF_CEHENNEMI_CODING_AGENT_SPEC_V2.md.json`. A targeted route-contract check (`uv run pytest backend/tests/test_openapi_contract.py -q`) passed **7/7**; do not substitute the live-Neo4j full suite for this read-only documentation audit.

When the assignment requests counts only, return exactly the claim counts (and targeted-test counts only if explicitly requested) after validating the JSON's exact keys, `doc_path`, positive integer count, arithmetic, failure-array length, and exact failure-object keys. Do not expand the final with evidence details.

The pre-fix report found eight drift/conflict findings: origin terminology (two claims), optional/unbounded candidate reads, missing source links, a no-op seed command, left-vs-right inspector placement, candidate review already implemented, and authentication already implemented.
