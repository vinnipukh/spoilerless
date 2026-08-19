# Phase 09 execution — auth-gate fallout, boundary-clamp test drift, session sweep epoch trap (2026-08-05)

Durable patterns from executing 09-03 (write-path auth), 09-04 (read-path
boundary hardening), and their test-update fallout. The common thread: when a
plan tightens server-side auth/visibility semantics, the OLD tests that
probed anonymously or unauthenticated break — fixing them is part of the
plan, not a regression.

## 1. Neo4j epoch-unit trap: `timestamp()` is MILLISECONDS, `time.time()` is SECONDS

Sessions store `expires_at` as a seconds epoch (`time.time()`-based, set in
`Neo4jSessionRepository.create` and checked by `get()` as `s.expires_at >
$now` with `$now = time.time()`). A sweep written as the docstring suggested
— `WHERE s.expires_at < timestamp()` — compares seconds against Neo4j's
millisecond `timestamp()` and treats **every** session as expired, deleting
all of them.

**Rule:** any Cypher time comparison against a property written by Python
`time.time()` must pass `$now = time.time()` as a parameter — never use the
bare Cypher `timestamp()` function. Symptom: sweep test `removed == 3`
(expected 2) → the "live" session was also swept. Fix (`sweep_expired`):
`WHERE s.expires_at < $now OR s.revoked_at IS NOT NULL` with `now=time.time()`.

## 2. Auth-gate fallout: old integration tests get 401 — add a user_session fixture

When a plan puts a mutation route behind `CurrentUserDependency` (09-03
gated candidate ingest, notes, custom nodes/rels, revision revert), existing
integration tests that POST unauthenticated flip from 200/422 to 401
(`AUTH_UNAUTHENTICATED`). Fix pattern (copied from `test_candidate_review.py`
— module-local, no shared conftest fixture):

```python
def _create_user_with_session(role="user") -> tuple[str, str]:
    # UserRepository(db).upsert(google_sub=f"test-{role}-{uuid4()}", ...)
    # + Neo4jSessionRepository(db).create(user["id"], ttl_seconds=3600)
    # via fresh driver + asyncio.run; returns (google_sub, raw_token)

@pytest.fixture
def user_session(live_client):
    google_sub, raw_token = _create_user_with_session("user")
    live_client.cookies.set("session", raw_token)
    yield google_sub
    asyncio.run(_delete_test_user(google_sub))  # MATCH (u:AppUser {google_sub}) OPTIONAL MATCH ... HAS_SESSION ... DETACH DELETE u, s
```

Then add `user_session: str` to each failing test's signature. Never delete
real dev user rows (runbook rule).

## 3. Anonymous-boundary-clamp: tests probing boundary 2/3 anonymously must authenticate

PROB-04/#12 clamps ANONYMOUS readers to effective boundary 1 (server-side,
in `graph.py` and `series.py`: `requested = 1 if user is None else
visible_until_order`). Tests that previously requested
`visible_until_order=2/3` anonymously now fail with `assert 1 == 2`
(`effective_view_order`/`visible_until_order` report 1) or "expected 422,
got 200" (anonymous order-4 probe is clamped, never a non-persisted 422).

Fix pattern — boundary-session fixture mirroring the existing ABOVE_VIEW
machinery (`test_graph_api.py`):

```python
async def _prepare_boundary_session(watched_through: int) -> str:
    # create :AppUser + :Session (fresh random token) + :UserSeriesProgress
    # with watched_through_order = view_as_of_order = visible_until_order = watched
async def _clean_boundary_session(watched_through: int) -> None: ...
def _boundary_headers(raw): return {"Cookie": f"session={raw}"}
```

Rules: boundary 1 stays anonymous; boundaries 2/3 use the session;
`test_graph_error_shapes` exercises the non-persisted 422 with an
AUTHENTICATED order-4 request (anonymous is clamped to 200/boundary-1).
Same pattern applies to episode-list tests (`test_episode_masking.py` has its
own `_prepare_progress_fixture(watched, view)` — reuse it).

## 4. `npm run build` (tsc -b) catches test-file type errors that vitest misses

"Tests green" ≠ "typecheck green" for frontend work. A test-only typing
change — e.g. replacing `let captured: any = null` with
`let captured: ReturnType<typeof useRevisions> | null = null` — breaks TS
closure narrowing inside `vi.waitFor` callbacks (TS18047 'possibly null',
TS2339 'data does not exist on idle member' — the hook returns a
discriminated union on `status`). vitest runs fine (jsdom, no typecheck);
`npm run build` fails.

Fix (useRevisions.test.tsx): non-null assertions at access sites +
narrowing helpers:
```ts
type RevisionsState = NonNullable<ReturnType<typeof useRevisions>>
function dataOf(c: RevisionsState): RevisionResponse[] { return c.status === 'success' ? c.data : [] }
function errorOf(c: RevisionsState): ApiError | undefined { return c.status === 'error' ? c.error : undefined }
```
Then `expect(dataOf(captured!)).toEqual(...)`. Always run `npm run build`
after any executor returns frontend-touching work.

## 5. main.py lifespan additions: import asyncio

Adding a background sweep task (`asyncio.create_task`) to the FastAPI
lifespan requires `import asyncio` in `main.py` — it was not previously
imported, and the missing name surfaced as `NameError: name 'asyncio' is not
defined` at TestClient setup, failing every test in the module (52 errors).
Also: guard the sweep on `verify_connection()` success (else-branch of the
degraded-startup try/except) so a down DB skips the task cleanly.
