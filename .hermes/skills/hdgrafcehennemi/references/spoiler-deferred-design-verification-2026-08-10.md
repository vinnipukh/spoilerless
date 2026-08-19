# Deferred spoiler-design accuracy verification (2026-08-10)

Use this when auditing `docs/SPOILER-DEFERRED-DESIGN.md` or another future-invariants document against the live Spoilerless tree.

## Classification rule

- Do not fail a clearly labeled future feature merely because no implementation exists.
- Still verify embedded present-state claims: current paths/symbols, absence or shipped status, canonical data-model terminology, and analogies to existing boundary behavior.
- Treat a future rule as checkable when it claims to mirror a live mechanism; compare comparator direction and fail-closed behavior, not just field names.

## Boundary-direction evidence

Snapshot-style spoiler gates are safe at or below the current effective boundary:

- Chat history: `spoilerless/app/graph/chat.py` uses `message.visible_until_order_snapshot <= $visible_until_order`.
- ChangeSets: `spoilerless/app/repository/change_set.py` treats a snapshot as stale when it exceeds current progress.
- Therefore a future review with `spoiler_up_to_order` is eligible when `spoiler_up_to_order <= effective_view_order` and hidden when it is greater. Wording that hides a review when its spoiler order is *below* the reader boundary reverses the rule.

When a document both states the reversed comparator and separately claims it is “the same rule as chat messages and ChangeSets,” record two atomic failures: one for the comparator and one for the false equivalence.

## Current absence checks

Confirm deferred feature absence across registered API routers (`spoilerless/app/main.py`), backend domain/API/schema files, ontology/seed data, and frontend source. Avoid interpreting incidental words such as “review” in candidate-review test names as a Reviews product feature.

## Artifact discipline

Write only the requested verification JSON. Validate exact top-level/failure keys and count arithmetic. If canonical fresh evidence is requested, run a single temporary pytest that validates only the final artifact, then delete the temporary file; do not run live-Neo4j application suites for a static documentation audit.
