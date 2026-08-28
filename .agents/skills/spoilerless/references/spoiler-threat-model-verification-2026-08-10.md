# Spoiler threat-model accuracy verification (2026-08-10)

Use this reference when auditing a living spoiler/security threat model against the current Spoilerless tree. The verified artifact from this review was `.planning/tmp/verify-SPOILER-THREAT-MODEL.json` (77 checked, 46 passed, 31 failed).

## Audit method

1. **Separate four statuses explicitly:** modeled threat, desired mitigation, implemented control, and verified regression coverage. Historical plan language such as “07-05 adds” is not proof that code or tests landed.
2. **Verify global completeness claims first.** A statement such as “covers every leak class” fails when current public surfaces are absent even if each documented row is locally accurate. Enumerate live OpenAPI paths and inspect every spoiler-bearing read path.
3. **Check trust boundaries, not only Cypher predicates:**
   - anonymous graph reads are fixed at order 1;
   - authenticated reads are clamped to persisted `UserSeriesProgress`;
   - progress and mutation routes require current-user/admin dependencies as applicable;
   - ownership checks and token ownership are part of spoiler safety because one user must not widen or mutate another user’s view.
4. **Inspect complete query chains.** Do not infer Claim visibility merely because Evidence/Source and relationship visibility are gated. In `retrieval/tools.py`, `GET_EVIDENCE_QUERY` / `EVIDENCE_FOR_CLAIMS_QUERY` and `GET_SOURCES_QUERY` / `SOURCES_FOR_CLAIMS_QUERY` gate the relationship and returned node but do not gate the matched Claim, its endpoints, or validity window.
5. **Audit every current delivery surface:** graph GET, shortest path, Markdown export, chat, ChangeSets, and share-token snapshots. Share creation currently validates that the requested episode order exists but does not clamp it to the creator’s persisted progress; the token graph serves the stored boundary.
6. **Inspect non-query defenses:**
   - `retrieval/pipeline.py` boundary re-filtering, allowlisted rendered fields, fixed delimited context sections, item/character budgets, bounded tool replay, and current-turn-only citation validation;
   - `llm/system_prompt.py` untrusted-data framing;
   - security headers and explicit credentialed CORS in `main.py`;
   - Redis cache key boundary/user dimensions and invalidation behavior.
7. **Distinguish Redis failure modes.** Graph cache is best-effort and catches Redis errors, falling through to Neo4j. Configured rate limiting is not fully fail-open: `RedisBucket.init()` and `try_acquire_async()` are not wrapped.
8. **Validate regression commands semantically.** Confirm each named test file exists and each `pytest -k` selector matches at least one test; a zero-selection command is not coverage. Validate JSON artifact invariants with a focused temporary pytest: checked > 0, passed + failed = checked, failures length = failed, and each failure has exactly `line`, `claim`, `expected`, `actual`.
9. **Recount brittle metadata from HEAD.** During this review the live schema was 37 path templates / 50 operations, and `retrieval/tools.py` had 39 literal `$visible_until_order` occurrences. Old suite/lint baselines and literal counts should be refreshed or removed.

## High-value drift examples

- `spoiler/policy.py` now has centralized `is_visible` and effective-boundary helpers; future-tense “no helper yet” wording is stale.
- Episode masking currently uses episode `visible_from_order`; it does not consume `title_is_spoiler` or `title_visible_from_order`, even though the episode query returns them.
- The seed has six character `image_source_url` values and zero `image_url` values; do not conflate attribution URLs with image assets.
- Error codes are uppercase (`RESOURCE_NOT_FOUND`, `INVALID_VISIBLE_UNTIL_ORDER`, `CHANGESET_STALE`).
- Server graph caching exists with `graph:{series}:{boundary}:{user-or-anon}` keys and a 300-second TTL.
- `test_episode_metadata.py` and `test_media_safety.py` do not exist; current episode-title coverage is in `test_episode_masking.py`, `test_episode_ordering.py`, and `test_spoiler_policy.py`.
