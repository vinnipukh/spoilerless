# Dedup-wave lessons: test fixtures, live-DB probes, full-suite baselines

From the 08-11 ELEVENTH PASS (PROB-09 #61-#68/#72-#74/#77/#81/#71 + 503
root cause). All committed; each lesson is the failure mode we hit.

## 1. Required-constructor-param changes break test fixtures as 500s, not collection errors

`AuthService.__init__` made `session_repo`/`verifier` required (killed the
silent `or InMemorySessionRepository()` / `or ProductionGoogleVerifier()`
fallbacks). Seven test files (`test_settings_api`, `test_progress_api`,
`test_chat_api`, 4× `test_change_set_*`) built the service with only
`user_repo` + `session_repo`.

Symptom: a 66-failure storm across unrelated suites (settings + progress +
chat + user_content). Each failure was HTTP 500 — the fixture's
dependency-override function raises `TypeError` AT REQUEST TIME (inside
FastAPI dependency resolution), which `ServerErrorMiddleware` converts to
500 when the fixture uses `raise_server_exceptions=False`. It never
surfaces as a fixture/collection error, so the test files pass import and
the blame looks like DB-state residue.

Rules:
- Changing a constructor signature → `grep -rn "ClassName(" spoilerless/tests` BEFORE committing. Fix every fixture in the same pass.
- A 500-on-every-request pattern across suites whose fixtures build the
  same service class = check the dependency-override construction first.
- Shared no-op: `NoopGoogleVerifier` lives in `tests/conftest.py` — import
  it, never re-declare per file.

## 2. Scripted stub-insertion pitfall: match the DEFINITION, not the identifier

The first auto-patch replaced call sites (`AuthService(..., verifier=_NoopVerifier())`)
then gated the class insertion on `if "_NoopVerifier" not in src` — the
replacement had already put that string in the file, so the class was
NEVER defined → `NameError` at request time → the 500 storm. The class
definition was missing from all 3 files.

Rule: when a script both rewrites call sites and conditionally inserts a
definition, gate on the DEFINITION form (`if "class _NoopVerifier" not in
src`), or insert the class unconditionally first. Verify after with
`grep -c "class X"`.

## 3. Debug probes on the live local-docker DB break the seed integrity audit

Probing the repo layer with ad-hoc scripts that write to `series_dexter`
(e.g. `MERGE (p:Progress {user_id: 'probe', series_id: 'series_dexter'})`)
leaves stray nodes with `visible_from_order = null`. The seed's
integrity audit (seed.py `raise ValueError` on any story-series node with
null `visible_from_order`) then fails EVERY suite whose fixture re-seeds →
101 fixture ERRORS, looking like a code regression.

Rules:
- Probe scripts must use a scratch series id, or delete their rows
  immediately after (`MATCH (p:Progress {user_id: $u}) DETACH DELETE p`).
- The 101-ERRORS-with-`seed.py:ValueError` signature = stray rows on the
  live series, not your code.

## 4. Transient single failure on a combined run, green isolated → residue, re-run

Twice this session: `test_sweep_removes_only_expired_and_revoked` and
`test_revert_of_canonical_override_note_...` failed on a combined
multi-file run, passed isolated AND on a full re-run. Leftover rows from
an aborted prior run (session/change-set residue) break count-based
asserts once, then get cleaned by the rerun's own teardown.

Rule: before chasing a new failure, re-run the exact failing test
isolated; if it passes, re-run the combined set. Only investigate if it
fails both times.

## 5. Full-suite baseline (post-503-fix), local docker

After the `WITH u, s` fix in `CHANGE_SET_CREATE_QUERY` (missing WITH
between MERGE and MATCH — strict Neo4j 5.x rejects with 42N24-class
errors, newer Aura engine tolerates it, which is why Aura stayed green),
the change-set family runs on local docker: **full suite = 584 passed /
7 failed** (3 doc-contract, 2 seed-image, 2 seed_idempotency
constraint-name — all documented pre-existing). Local docker is a viable
full-suite target for the change-set family now; no AuraDB-only
dependency remains for it.

Rule: run the FULL suite after each commit wave. Targeted suites
(e.g. 92+63 pass) missed the fixture breakage that the full suite
surfaced instantly.

## 6. Surface a hidden 500 with raise_server_exceptions

When a TestClient fixture uses `raise_server_exceptions=False` and a
route returns 500 with no logged traceback, temporarily flip it to
`True` in the fixture, run the single test, read the real exception
(`NameError: ... not defined` style), then revert. FastAPI's
ServerErrorMiddleware swallows the traceback into the response otherwise.
