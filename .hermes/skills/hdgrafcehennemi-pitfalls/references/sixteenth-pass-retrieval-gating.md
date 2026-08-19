# SIXTEENTH PASS — retrieval-hop visibility gating (2026-08-12)

Closed the ARCHITECTURE.md "Normative follow-ups" gap: every retrieval
query must visibility-gate the matched Claim and every hop before
returning rows/counts.

## Fix shape (spoilerless/app/retrieval/tools.py, commit 4ffb36b)

- `EVIDENCE_FOR_CLAIMS_QUERY`, `SOURCES_FOR_CLAIMS_QUERY`,
  `GET_EVIDENCE_QUERY`, `GET_SOURCES_QUERY` gated the SUPPORTED_BY /
  REFERS_TO relationship + the evidence/source node but NOT the Claim
  itself. A model-supplied hidden claim id returned its attachments —
  hidden claim existence revealed through the claim_id column.
- All four now embed the shared `visible_claim_where()`
  (spoiler/app/spoiler/filter.py) on the claim hop — the same predicate
  the claim-list queries use. Neighborhood/summary callers pass
  already-visible claim ids, so those paths are behavior-unchanged;
  direct tool calls with hidden ids fail closed (identical to missing id).
- `EPISODE_CODES_QUERY` / `fetch_episode_codes` deliberately untouched:
  internal enrichment over already-visible rows, never model input.
- Suite: 592 passed / 1 skipped (baseline 591 + 1 new test).

## Pitfall 1 — stub fragment-routing order (test_retrieval_pipeline.py)

`_StubDatabase` routes queries by distinctive Cypher fragment text, first
match in dict order. Adding `visible_claim_where()` to the evidence/sources
queries put `claim.claim_type` into them → they matched the claim fragment
BEFORE `SUPPORTED_BY` / `REFERS_TO` → evidence rows became claim rows →
dedup tests failed with confusing context-assembly assertions (a claim
counted twice in the assembled context), NOT a routing error message.

Rule: when a shared WHERE fragment moves into more queries, re-check
fragment-order routing stubs. Order constraint: `SUPPORTED_BY` /
`REFERS_TO` must route BEFORE `claim.claim_type`; `note.user_id` stays
before `REFERS_TO` (USER_NOTES_QUERY contains both).

Also: query constants built by concatenating a helper fragment need the
parenthesized form (`QUERY = ( """...""" + helper() + """...""" )`) —
the bare `QUERY = """...` + indented continuation is an IndentationError.

## Pitfall 2 — vacuous MATCH-anchored CREATE in scratch tests

The leak-reproduction test built its fixture with
`MATCH (subject {...}) ... CREATE (claim ...)` — the anchor nodes never
existed, so the whole statement silently created NOTHING and the test
PASSED on an empty graph (green before the fix = vacuous, the leak was
still open).

Rule: when a test must FAIL pre-fix, confirm the fixture actually created
rows (use CREATE for the anchor nodes, not MATCH). Red-green both runs
matter: a first run that passes before the fix is a fixture bug, not a
closed gap.

## Test pattern that caught the real leak

The seeded-series hidden claim (CLAIM_HARRY_FAMILY, s01e03) has hidden
evidence too, so `test_get_evidence_visible_only` passed despite the gap.
The leak needs a hidden-claim + individually-visible-attachment case:
scratch series, claim `visible_from_order: 99`, evidence/source/rels at 1,
then assert `get_evidence`/`get_sources` return the same empty list as a
missing id.
