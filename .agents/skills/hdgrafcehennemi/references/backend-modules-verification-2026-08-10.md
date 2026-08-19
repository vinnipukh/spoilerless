# BACKEND-MODULES verification snapshot (2026-08-10)

Use this when auditing `docs/BACKEND-MODULES.md` against the live backend. The completed static audit checked 192 concrete claims: 184 passed and 8 failed. Artifact: `.planning/tmp/verify-BACKEND-MODULES.json`.

## Durable audit method

1. Read the whole doc with line numbers.
2. Inventory every `spoilerless/app/**/*.py` and `spoilerless/tests/test_*.py` file with AST-derived top-level symbols.
3. Parse API decorators and function annotations to verify route families, auth dependencies, and API→service/repository paths.
4. Parse imports to check dependency direction, then read composition-root and transaction code for runtime wiring rather than trusting module docstrings.
5. Inspect Pydantic inheritance/config directly: plain `BaseModel` defaults to ignoring extra fields; only `extra='forbid'` or a strict base proves rejection.
6. Trace cache invalidation per mutation route, not per module. A family-level statement can be false even when graph-visible subroutes invalidate correctly.
7. Distinguish methods from properties and defaults from the layer that actually owns them.
8. For managed-write claims, inspect callback bodies and helpers for retry-generated UUIDs/timestamps—not just `Neo4jDatabase.execute_write()` documentation.
9. Validate the final JSON with the standard artifact validator and a targeted, database-free pytest artifact test; do not run the live Neo4j suite for a static documentation audit.

## Verified stale/overbroad claims

- `api/` is not uniformly router-bearing: `api/deps.py` and `api/__init__.py` have no `router`.
- Note create/update/delete do not invalidate graph cache; custom-node/custom-relationship mutations do.
- Graph and series response models inherit plain `BaseModel` and do not reject extra fields.
- `RateLimiter.bucket_key` is a property, not `bucket_key()`.
- Share TTL default (`2592000`) lives on repository protocol/implementations; the API omits the argument.
- The immutable/retry-stable managed-command rule is not universally honored: candidate/revision paths pass dict commands, and `RevisionRepository.log_revision()` generates `uuid4()` inside transaction callbacks.
- Direct custom relationships derive visibility inline in Cypher; only direct custom-node creation calls `derive_visible_from_order()` (notes copy target visibility).
- `user_id` is server-injected for `propose_changeset` as well as `get_user_notes`; “only for notes” is true only within the read-tool executor map.

## Precision lessons

- Treat a sentence with several clauses as one failed claim when any concrete clause is contradicted, but explain exactly which clause failed.
- Flag only source-verifiable mismatches; do not convert normative extension advice into a failure unless live code is explicitly described as already following it.
- Keep failure entries at the doc line that contains the claim and use exact `line`, `claim`, `expected`, `actual` keys.