# Session lessons — ELEVENTH PASS execution (2026-08-11/12)

Durable pitfalls from the PROB-09 wave execution + a gsd-docs-update refresh
run. Each entry is a pattern that bit once and will bite again.

## 1. Required-constructor-param changes MUST sweep test fixtures first
Changing a service/class `__init__` from `optional with fallback` to
`required params` (e.g. AuthService dropping `session_repo or
InMemorySessionRepository()` / `verifier or ProductionGoogleVerifier()`)
breaks every test file that constructs the class in its dependency-override
helpers (`_build_app` / `_authed` fixtures).

The breakage is SILENT at collection: the fixture TypeError fires at
dependency-resolution time inside the request → Starlette
ServerErrorMiddleware converts it to a plain 500 → an entire test file's
assertions fail (settings/progress/chat/change-set all went 500 at once —
looked exactly like a DB-outage storm, 66 failures).

Pattern:
- BEFORE committing a required-param change: `grep -rn "ClassName(" spoilerless/tests`
  and add the missing arg to every construction site.
- Add ONE shared stub to `conftest.py` (e.g. `NoopGoogleVerifier`) and
  import it — never a per-file inline copy.
- If a storm of unrelated-looking 500s appears after a DI-related commit,
  check the fixture constructors BEFORE blaming the DB or your query change.

## 2. Inline-stub insertion bug (scripted class injection)
When scripting "insert stub class if not present":
`if "StubName" not in src` FAILS after you replaced the call site — the
replacement text already contains `StubName`, so the definition is never
inserted → NameError at runtime (test_settings_api.py:128 pattern).
Check for `class StubName:` (the definition), not the bare name.

## 3. TestClient raise_server_exceptions=False hides the real error
The repo's TestClient fixtures use `raise_server_exceptions=False` — any
server-side exception (dependency TypeError, NameError in a handler) becomes
a bare 500 response with NO server-side log visible in pytest output.
To diagnose: temporarily flip the fixture to `raise_server_exceptions=True`,
run the single failing test, read the real traceback, then revert. The flip
surfaces even errors the app's handlers swallow.

## 4. Transient residue on shared live docker Neo4j — retry before chasing
First combined-run failures are often residue from a previous aborted run
(leftover rows on the scratch series or the seeded series), NOT a code
regression. Seen 3× this session (sweep test, revision test, candidate test):
- Run the failing file ISOLATED → green? Then re-run the combined set →
  green again? → residue, not your change.
- Documented baseline: full local-docker suite = **584 passed / 7 failed**
  (3 doc-contract, 2 seed-image, 2 seed_idempotency constraint-name).
  Anything else is a regression to investigate; but retry once first.

## 5. Probe writes pollute the seed integrity audit
Any ad-hoc probe script doing `MERGE (p:Whatever {series_id: 'series_dexter'})`
without a `visible_from_order` property breaks `_check_visibility_schema`
(seed.py ValueError "Seed integrity audit failed: N node(s) with null
visible_from_order") → 101 fixture collection errors across MANY test files
(the audit scans all nodes with the series_id, label-agnostic).
Clean up probe rows immediately (`MATCH (p:Label {user_id: $u}) DETACH DELETE p`)
or probe with series_ids outside the seeded series.

## 6. Neo4j 5.x strictness: `WITH` required between MERGE and MATCH
`MERGE (u) MERGE (s) MATCH ...` raises 42N24 on local docker 5.x while the
newer AuraDB engine tolerates it. The 28-change-set-test 503 storm was ONE
missing `WITH u, s`. Symptoms: query works on Aura, 503s on local docker with
"database request could not be completed" — the app's error handler masks the
driver exception. Surface the real error by running the failing query
directly or via `--log-cli-level` on a probe, before touching the query.
Note (PROB-09/#81): ClientError is no longer 503-masked — bad Cypher now
surfaces as a plain 500, which is the correct signal (server bug, not infra).

## 7. Ledger claims are hypotheses — verify before patching
PROBLEMS.md entries were wrong twice this session: #61's "App.test mock
missing switchSeries" (App.test never mocks the hook; real cause: Radix
Select doesn't fire onValueChange for a re-selected value after
`switchSeries` pre-set viewAsOfOrder=1 → fail-closed null fixes it) and the
TENTH-PASS "blocked" framing. Grep the claim's target before editing; the
ledger documents what someone believed, not always what is.

## 8. gsd-docs-update on this repo (refresh-run quirks)
- `gsd-tools.cjs query docs-init` reports `has_api_routes: false` on this
  Python/FastAPI project (Python-blind signal detection) — API.md must be
  codebase-discovered and queued manually. `has_package_json`/`has_tests`
  are also false (uv/pytest) — treat project_type signals as advisory.
- node on MSYS mangles `$HOME` → `C:\c\Users\...`; invoke the shim with a
  Windows-style path: `node "C:/Users/<user>/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs"`.
- A prior run's `.planning/tmp/docs-work-manifest.json` persists (status
  "verified", claim counts) — re-running refreshes all 9 canonical docs
  against current code; rewrite the manifest queue with fresh
  `status: pending` per wave, then dispatch writer batches.
- Writers VERIFY against source and correct stale claims (they caught
  SYSTEM_PROMPT_VERSION, `--project spoilerless` commands, NODE_LABELS
  location) — trust their source-checked corrections, but spot-check the
  GSD marker stays line 1.
