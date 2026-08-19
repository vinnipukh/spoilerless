# Retrieval-hop gating + stub routing order (2026-08-12, SIXTEENTH PASS, 4ffb36b)

## The code invariant

Every retrieval query that MATCHes a `Claim` must visibility-gate the claim
hop itself — NOT just the relationships/nodes it projects. Gap found:
`EVIDENCE_FOR_CLAIMS_QUERY`, `SOURCES_FOR_CLAIMS_QUERY`, `GET_EVIDENCE_QUERY`,
`GET_SOURCES_QUERY` gated `supported`/`ref` rel + evidence/source node but
never the claim anchor. A model-supplied hidden claim id (get_evidence /
get_sources tools take arbitrary `claim_ids` from the model) returned its
attachments → revealed the hidden claim's existence.

Fix (committed `4ffb36b`): all four queries now append
`visible_claim_where()` on the claim hop (the shared D-20 predicate:
non-null boundary, canonical/candidate origin, non-user claim_type, validity
window). Neighborhood/summary callers pass already-visible claim ids, so the
added predicate is a no-op there — the gate is defense-in-depth + the
tool-input path.

Regression test: scratch-series case — hidden Claim (`visible_from_order: 99`)
with individually visible EvidenceFragment + Source + rels (order 1) must
return the same empty result as a missing id.

## Stub fragment routing is ORDER-SENSITIVE (the gotcha that broke 2 tests)

`_StubDatabase` (test_retrieval_pipeline.py) routes queries by distinctive
Cypher fragments in dict order. `visible_claim_where()` contains
`claim.claim_type <> 'user_authored'`, so widening it into the
evidence/sources queries made the `"claim.claim_type"` fragment NON-distinctive:
`EVIDENCE_FOR_CLAIMS_QUERY` matched the claim fragment first (dict order) and
returned `claim_rows` instead of `evidence_rows` → the claim rendered twice in
assembled context (dedup test `assert count == 1` failed) and tool-result
truncation tests broke.

Rule: when a shared WHERE fragment (visible_claim_where / claim_projection)
gains new query call sites, re-check the stub's fragment order. The routing
fragments must be ordered most-specific-first:
`SUPPORTED_BY` and `REFERS_TO` BEFORE `claim.claim_type` (evidence/sources
queries legitimately contain both now). `note.user_id` must stay before
`REFERS_TO` (USER_NOTES_QUERY contains both).

## Vacuous test trap: MATCH-then-CREATE in test Cypher

`MATCH (subject {id: ...}) MATCH (object {...}) CREATE (claim ...)` silently
creates NOTHING when the anchor nodes don't exist — the test passes trivially
("leak reproduced" test first ran green before the anchors were added).
When seeding scratch data, CREATE the anchor nodes in the same statement
(`CREATE (subject:Character {...}) CREATE (object:Character {...}) CREATE
(claim:Claim {...})`). A leak-repro test MUST be verified to actually fail
before the fix, or it proves nothing.

## Query constant syntax

Appending a predicate fragment to a query constant requires the parenthesized
form used by CLAIMS_FOR_FRONTIER_QUERY:
```python
NAME = (
    """\
MATCH ...
WHERE claim.id IN $claim_ids
  AND """
    + visible_claim_where()
    + """
  AND supported.visible_from_order IS NOT NULL
...
"""
)
```
Plain `NAME = """\ ... """ + fn()` breaks with IndentationError.

## Test commands (unchanged)

- Full BE suite (local docker only): `source scripts/env-local.sh && unset
  PYTHONPATH && .venv/Scripts/python.exe -m pytest spoilerless/tests -q -p
  no:cacheprovider` — 592 passed / 1 skipped baseline after this pass.
- New retrieval tests live in the scratch series (`series_scratch_retrieval`,
  fixture teardown deletes `{series_id: SCRATCH_SERIES}` nodes) — never pollute
  `series_dexter`.
