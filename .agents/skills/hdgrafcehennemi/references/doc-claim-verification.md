# Doc-claim verification against live code (this repo)

Task shape: verify-subagent assignments re-check a `docs/*.md` file against live
code and emit a JSON artifact at `.planning/tmp/verify-<DOC>.json`. Root helpers
exist: `verify_all_claims.py`, `run_doc_verification.py`, `run_verification.py`.
Baseline artifacts carry counts (e.g. `verify-DEPLOYMENT.json` 96 checked /
18 failed before fixes; `verify-README.md.json` 169/169 as of 08-14) — a
re-verify compares against that. README.md verified facts live in
`references/08-14-readme-doc-facts.md`.

Sibling reference for doc-writer update mode: `references/08-14-testing-doc-facts.md`
(current TESTING.md facts, verified 08-14) — `references/testing-doc-baseline.md`
(08-12) is SUPERSEDED on the baseline counts (584/7 retired by PROBLEMS.md
NINETEENTH PASS, 2026-08-13).
CONFIGURATION.md: `references/08-14-configuration-doc-facts.md` (verified 08-14,
90/90 PASS, 5 VERIFY markers; baseline `.planning/tmp/verify-CONFIGURATION.md.json`).
DEPLOYMENT.md: `references/08-14-deployment-doc-facts.md` (writer facts 08-14;
verifier pass 08-14 re-confirmed 101/101 PASS; baseline
`.planning/tmp/verify-DEPLOYMENT.md.json`).
frontend-components.md: `references/08-14-frontend-components-doc-facts.md` (verified 08-14,
187/189 PASS, 2 failures — stale L294 readOnly integration note + missing `graphStylesheet`
export; baseline `.planning/tmp/verify-frontend-components.md.json`; the older
`verify-FRONTEND-COMPONENTS.json` naming is superseded).
backend-modules.md: **FINAL re-verify 08-16 (iteration 2) = 659/659 PASS, `failures: []`**
baseline `.planning/tmp/verify-backend-modules.md.json` OVERWRITTEN. History: first pass
427/419+8; re-verify 08-16 = 578/580 with 2 NEW BLOCKERs the first pass missed (L220
`_TOOL_INPUT_MODELS` + L221 `_TOOL_EXECUTORS` — replaced by the single `TOOL_SPECS`
registry, PROB-09/#63; the identifiers survive only in the pipeline.py:425 comment, so a
bare occurrence grep false-PASSes); iteration-2 fix (2 edits) rewrote both lines to
`TOOL_SPECS` (per-spec `input_model`/`executor` fields) → fresh full re-verify = 659/659.
Tally method: automated extraction (504 paths/symbols/APIs/test-files) + 13 bare `/api`
route claims + 8 pyproject deps + 134 curated behavior checks — differs from the 580
per-line tally by method; compare PASS/FAIL state, never the raw count.

## JSON contract (strict — parent enforces it)
- Keys: `doc_path`, `claims_checked`, `claims_passed`, `claims_failed`, `failures`.
- `claims_checked` positive; `claims_passed + claims_failed == claims_checked`;
  `len(failures) == claims_failed`.
- Each failure: `{line, claim, expected, actual}` (line = doc line number).
- Generate with a Python script using asserts for the count identities, then
  re-parse the written file to confirm validity before reporting.

## Workflow
1. Read the FULL doc (paginate; docs run 500+ lines).
2. Enumerate claims with doc line numbers — one claim per checkable statement
   (tables, code blocks, commands, config defaults, absence claims like
   "no Dockerfile tracked").
3. Verify each against live code:
   - exact command strings VERBATIM (e.g. render.yaml `startCommand` vs the
     doc's Start Command — copy the string, don't eyeball);
   - config defaults (`spoilerless/app/core/config.py`) vs documented defaults;
   - route wiring (grep rate-limiter deps, `RequireAdminDependency`, CSRF deps);
   - cache invalidation scope (grep `invalidate_series` call sites per route file);
   - absence of files (`ls Dockerfile .dockerignore`, no `envVars:` in render.yaml).
4. Phrasing check (the big one after "surgical fixes"): dashboard/platform state
   must be phrased as *intended* / *unknown from source control* + operator-step
   `<!-- VERIFY: ... -->` markers — NOT asserted facts. A claim PASSES when the
   doc correctly frames external state as unverifiable from the repo, even though
   the state itself is unconfirmed.
5. Count the VERIFY markers and require the documented count (`grep -c 'VERIFY:'`).
6. When a doc documents a KNOWN BUG (e.g. missing `invalidate_series` on
   revision revert, middleware without exception branch), the claim is "doc
   accurately describes the limitation" — verify the code STILL exhibits it:
   fixes land in code without the doc being updated, so every known-bug claim
   must be re-checked each pass. Verified 08-14 (DEPLOYMENT.md update): the
   undefined-`logger` NameError in the session/share sweep is FIXED —
   `spoilerless/app/main.py` defines `log = logging.getLogger(__name__)` (line
   40) and the sweep loop catches exceptions with `log.exception(...)` — "a
   failed sweep iteration is logged, never fatal" (main.py:139). The old doc
   claim ("exception branch calls undefined `logger` → NameError") was stale
   and was removed from DEPLOYMENT.md. Still-live known bugs: revision revert
   omits `invalidate_series(series_id)` (`spoilerless/app/api/revisions.py`
   has no invalidate call; candidates.py/change_set.py/user_content.py do);
   request-logging middleware logs only after `call_next` returns with no
   try/except/finally (`_request_logging_middleware` in main.py).

## Re-verify-after-fixes focus list (what the parent names explicitly)
- exact strings (Render Start Command must equal render.yaml verbatim);
- code-behavior claims: invalidation scope incl. revision-revert omission;
  session/share sweep undefined-logger NameError; request-logging coverage
  limited to completed requests (no try/finally/except);
- local env guidance (`.env.example` sets `VITE_API_BASE_URL=/api`; client.ts/
  chat.ts prepend base to paths already starting with `/api` → `/api/api` —
  doc must tell users to delete/set-empty it);
- VERIFY marker count preserved (DEPLOYMENT.md = 14 as of 08-14 — the "13"
  in older notes predates the v1.3/10-11 doc update, which added one; ALWAYS
  `grep -c 'VERIFY:'` the live file and report the on-disk count, never a
  hard-coded number from a reference);
- dashboard-only state rephrased as operator steps, not asserted facts.

## Pitfalls (this host)
- `search_files` can error "path not found" (Turkish: *Sistem belirtilen yolu
  bulamıyor* / os error 3) on paths that verifiably exist — the path gets
  MSYS-mangled to `/c/...` before rg runs. Fallback: `cd` to repo root and use
  terminal `grep -rn`, or `read_file` directly. Never conclude the file is
  missing from that error alone.
- `read_file` accepts both `C:\...` and `C:/...` forms fine; the search tool is
  the one that mangles.
- Verify fixture claims against data files (`data/dexter/metadata/episodes.json`
  codes S01E01–S01E03; seed uses MERGE → idempotent), not just doc prose.
- MSYS `/tmp` is invisible to Windows python: bash `cp` to `/tmp/x.json` then
  `json.load(open("/tmp/x.json"))` in execute_code → FileNotFoundError. Resolve the
  real path first (`cygpath -w /tmp`) or keep shared temp files under `.planning/tmp/`.
- Check installed-package claims via `node_modules/<pkg>/package.json` (e.g.
  jsdom engines `^22.22.2 || ^24.15.0 || >=26.0.0`).

## Doc-writer update mode — drift traps fixed in CONFIGURATION.md (verified 2026-08-12)
Facts checked against live code while updating docs/CONFIGURATION.md; trust these over
any task-brief summary:
- `uv run --project spoilerless python -m spoilerless.app.graph.setup` — re-verified
  08-14: `--project spoilerless` actually WORKS even though `spoilerless/pyproject.toml`
  does not exist (uv resolves the project from the parent directory; probe
  `uv run --project spoilerless python -c "print(1)"` prints). ci.yml's verbatim use
  of this form is therefore NOT a doc error — never "fix" CI verbatim strings on
  this basis. Canonical local form remains `uv run python -m spoilerless.app.graph.setup`
  or `uv run spoilerless-setup` (root `[project.scripts]`).
- `frontend/vite.config.ts` DOES set `envDir: '..'` — `VITE_*` vars come from the ROOT
  `.env`; `frontend/.env.local` does not exist and would be ignored; `frontend/.env.example`
  is a reference-only template (declares `VITE_GOOGLE_CLIENT_ID` + commented
  `VITE_API_BASE_URL` with example origin `https://api.spoilerless.net`). Task briefs that
  say "envDir NOT set — frontend reads its own dir" are stale.
- `SYSTEM_PROMPT_VERSION` does not exist anywhere in `spoilerless/`; `llm/system_prompt.py`
  exposes `SYSTEM_PROMPT_ENG`, `SYSTEM_PROMPT_TR`, and a `SYSTEM_PROMPTS` mapping
  (English fallback for unknown languages).
- `AuthService` takes NO repository/verifier defaults (PROB-09/#77 removed the silent
  `InMemorySessionRepository()` / `ProductionGoogleVerifier()` fallbacks);
  `InMemorySessionRepository` is dev/test-only, constructed explicitly by tests. The
  FastAPI app wires `Neo4jSessionRepository` in `main.py` lifespan.
- Ontology `require_*()` validation runs in `seed.py`'s `setup_database()` (invoked by
  `setup.py` via `async_main`), not in `setup.py` itself.
- `NODE_LABELS` is defined in `graph/labels.py` (re-exported by `seed.py`);
  `RELATIONSHIP_TYPES` is defined in `seed.py`. Seed data lives under
  `data/dexter/{seed,metadata}/`.
- Task-brief "test X is stale" claims can themselves be stale: the 08-14 brief
  called `test_openapi_contract.py` stale (32 paths, DELETEs all 204) but the live
  file had already been updated to lock 39 templates with typed deletes (Phase 10
  10-03/10-06). Re-verify staleness claims against live asserts exactly like counts —
  the file's own comment ("instead of the stale 45-op/32-path set") reveals the update.
- Fastest ground truth for doc counts: run the suites. `NODE_ENV=test CI=1 npx vitest run`
  (~30s, gave 404/44 on 08-14) and `unset PYTHONPATH && uv run python
  scripts/run_phase10_backend_tests.py` (~2 min, all 11 chunks PASS) beat any prose.

## Verifier-pass technique (batch scripts — fastest path on this host)
Instead of many small Read/Grep round-trips, run ONE `execute_code` script per
batch using plain `pathlib` reads + regex (pure filesystem, no shell): it
sidesteps the search_files MSYS `/c/...` mangling AND collapses 20+ greps into a
single call. Patterns that worked 08-14 (ARCHITECTURE.md verify pass):
- Count symbol occurrences PER FILE to verify "N call sites" claims; separate
  def/import occurrences from call sites (e.g. `visible_claim_where`: filter.py 4
  = 1 def + 3 sites; tools.py 9 = 8 sites + 1 import; total 11 sites ✓).
- pydantic-settings defaults are multiline `Field(\n default=...)` blocks —
  single-line regexes return NOT FOUND; use re.S and capture the field block.
- config.py FIELD-NAME trap (hit 08-14 DEPLOYMENT.md pass): settings fields are
  snake_case (`session_cookie_name`, `neo4j_uri`), NOT the UPPER env names — a
  regex for `SESSION_COOKIE_NAME` returns ABSENT. Search snake_case field names
  or just read `spoilerless/app/core/config.py` directly (~170 lines).
- Route-location trap: `GET /api/series/{series_id}/graph` lives in `api/graph.py`
  (prefix `/api/series`), NOT `api/series.py` (only `''`, `/{series_id}`,
  `/{series_id}/episodes`); `GET/PUT /api/settings/llm` in `api/settings.py`
  (prefix `/api/settings`, paths `/llm`). Grep the api/ dir for the path string
  before concluding a route module is missing.
- `ERROR_CODES` is a `frozenset[...]` block — count quoted strings inside the
  braces, not `r'CODE:'` patterns.
- Route inventories: decorators span lines and use prefix-only paths
  (`@router.get(\n "/graph")`, `@router.get("")` with APIRouter prefix) —
  use a multiline-tolerant regex or you will undercount.
- Design figures (12–28 target nodes, <35 preferred edges, 5–20 Answer Graph)
  are NOT code constants — they live in `docs/decision-logs/phase-10-visualization.md`
  (DEC:D-09, REQ:VIZ-08/D-27). Check the decision log before failing a bounds claim.
- Budget: WRITE the result JSON EARLY — right after the decisive focus checks, even with provisional counts — then keep verifying and re-write it at the end. The 08-15 API.md pass proved the hard way: ~15 evidence batches consumed the whole tool-iteration budget and the run was cut off with the tally never written (all 88 claims had PASS evidence; the artifact did not exist). The JSON artifact is the deliverable; the one-liner is not. Consolidate harder too: route inventory + per-route deps + rate-limit constants + registry counts fit in 3–4 scripts, not 15.
- Per-route dependency wiring in ONE call: split the router file on `\n(?=@router\.)` and regex each route function's signature for dependency names (`CsrfGuardDependency`, `RequireAdminDependency`, `CurrentUserDependency`, `OptionalUserDependency`, `RateLimiter`) — decisive CSRF/admin-gate evidence without trusting bare name counts (occurrence counts include the import line: 5 `CsrfGuardDependency` in candidates.py = 4 decorators + 1 import; 4 `RequireAdminDependency` = 3 routes + import). Verify per-route, never per-file.
- Signature-scan blind spot: routes can inject the user dep under an alias — graph.py `get_visualization`/`get_expansion` show NO user param in the signature but use `user: dict | None = Depends(get_optional_current_user)`. When a route's signature shows no session dep but the doc claims session/boundary semantics, body-scan for `Depends(get_optional_current_user)` / `Depends(require_current_user)` before calling the doc wrong.
- Type-alias dep variant (hit 08-16, the one that hides EVERYTHING): most deps inject as `Annotated[..., Depends(x)]` aliases — `user: CurrentUserDependency`, `_admin: RequireAdminDependency`, `_csrf: CsrfGuardDependency`, `service: GraphServiceDependency`. The signature then contains NO `Depends(...)` call at all. Scan each route signature for BOTH `Depends(name)` AND `:\s*[^=,)]*<AliasName>` annotations, or you'll conclude gated routes are unauthenticated (candidates/change_set/settings/progress/share showed zero deps under a Depends-only scan).
- Decorator `status_code`/`dependencies=` live AFTER the path string: regex-matching only `@router.(method)(\s*"path"` captures the path but misses `status_code=201` later in the same decorator. Capture the full decorator text (from `@router.` up to `def `) and regex THAT for status codes (201/204 claims) and `dependencies=[...]`.
- `find()` start-offset trap: a term like `_ERROR_SPECS` can first match inside an earlier comment ("see _ERROR_SPECS below"); anchor with `find(name, find("DEFINING_CONST"))` or dump the module when small (config.py at 169 lines beat any regex).
- Hidden-route nuance: `include_in_schema=False` handlers (HEAD /health) exist
  in code but not in openapi — contract-test counts (52 ops / 39 templates)
  match openapi only; registered handlers can be +1.
- Verify "N route modules" by counting resource files in `api/` and excluding
  deps.py/exceptions.py/__init__.py, not by trusting the doc's own count.

## Phase-10 decision-log pass (2026-08-16) — dated claims + archived planning paths

`docs/decision-logs/phase-10-visualization.md` verified 46/61. Two traps that will
recur on ANY doc referencing phase-10 artifacts:

1. **`.planning/phases/10-polish-finishing-touches/` is EMPTY** since commit e62e664
   ("chore: archive v1.3 milestone", 2026-08-14 19:12). All phase-10 artifacts
   (10-0X-PLAN/SUMMARY, 10-UI-SPEC, 10-RESEARCH, 10-PATTERNS, 10-VALIDATION,
   10-CONTEXT, 10-DISCUSSION-LOG, 10-VERIFICATION) now live at
   `.planning/milestones/v1.3-phases/10-polish-finishing-touches/`. The decision
   log's coverage table still names `.planning/phases/...` (15 refs) → FAIL each
   with `actual` = "exists at milestones path (archive e62e664)". The doc's last
   edit (3988f15, 01:14) predates the move — stale, not historical.
   NOTE: `scripts/verify_phase10_coverage.py` validates ids/rows only (duplicates,
   missing/extra, malformed, empty, evidence_ref==source_id) — it does NOT check
   that `evidence_ref` file paths exist, so path drift never breaks the audit.

2. **Adjudicating dated counts in decision logs via git ordering** — the header's
   "14 passed" looked wrong (live file has 15 `def test_` fns, no skip/xfail/
   parametrize, no addopts). Check commit order:
   `git log --format='%h %ci %s' -- <doc>` and `-- <referenced test file>`.
   4903b23 (17:48) wrote the doc when the file had 14 tests; 761c818 (20:32) added
   the 15th (`@pytest.mark.benchmark` test_benchmark_harness_schema...). Claim was
   ACCURATE at doc date → PASS as history; note the live delta in the summary.
   The `-k "variant or bound"` count (7) still matches live.

Fixture/benchmark fact bank (verified this pass — reuse instead of re-deriving):
- `spoilerless/tests/fixtures/visualization/{s01e01_safe,s01e02_cumulative_safe}.json`:
  top keys `fixture_metadata` (effective_view_order 1/2, projection_version "1.0.0",
  immutable), `events` (tier: 1×major / 2×major), `graph` {nodes[type], edges[type],
  claims, sources, evidence}. File bytes 7,692 / 12,386 = the doc's payload cells.
  Baseline table (11/17 nodes, 7/14 edges, 4/1/3 & 6/2/5, node kinds, edge types)
  verifies by direct json.loads + Counter — no test run needed.
- Variant table (A 9/4, B 8/4, A·E02 13/7, B·E02 11/7 + kinds) is asserted verbatim
  in `test_variant_a_metrics_and_omissions` / `test_variant_b_metrics_and_omissions`
  (~lines 512-566); bounds 12/28/40/35/60 in `test_variant_evidence_object_shape`
  (~665); stability (retention 1.0, shared 6, displacement 0.0) in
  `test_variant_stability_between_episodes`. Grep the asserts, don't recompute.
- `scripts/benchmark_visualization.py`: `SEED = 0x1008` + `random.Random(SEED)`;
  `REQUIRED_SIZES` (30,50),(75,150),(150,400),(300,1000); exactly 16 `gates.append(`
  per size → structural evidence for "16/16 hard gates".
- `scripts/verify_phase10_coverage.py`: `EXACT_SOURCE_IDS` frozenset = 98 ids.
  Doc coverage table = 98 data rows — the header row (`| source_id | ... |`) is
  NOT `|---`, so filter it explicitly or you count 99.

### Iteration-2 re-verify — 64/64 after archival-note fix + phantom correction (2026-08-14+)

L251 phantom (`10-10-11-SUMMARY.md`) fixed → `10-11-SUMMARY.md`; with the doc's
2026-08-14 archival note (commit `e62e664` confirmed via
`git log --oneline -1 e62e664`) ALL 14 archived `.planning/phases/...` refs (13
table evidence_refs + L4 10-01-PLAN.md) PASS under HISTORICAL-RECORD semantics →
64/64, `failures: []`. Reusable traps from this pass:

- **Archive-resolution double-nesting trap**: to resolve
  `.planning/phases/10-polish-finishing-touches/<f>` against the archive, strip the
  WHOLE `10-polish-finishing-touches/` segment and join directly under
  `.planning/milestones/v1.3-phases/`. `alt = ARCH / path[len(".planning/phases/"):]`
  double-nests (`.../v1.3-phases/10-polish-finishing-touches/10-polish-finishing-touches/<f>`)
  and false-FAILs every archived ref. Use
  `path.removeprefix(".planning/phases/10-polish-finishing-touches/")`.
- **Benchmark-table claims: run the harness instead of counting gates.** A live
  `uv run python scripts/benchmark_visualization.py` reproduces the doc table
  verbatim (30x50 15n/13e + 27n/28e, 75x150 22n/37e cap_raised, 150x400 25n/46e
  cap_raised, 300x1000 28n/60e cap_raised, gates=16/16 every size, schema errors 0).
  CORRECTION to the fact-bank bullet above: the file contains 16 `gates.append(`
  TOTAL, not 16 per size — the run output is the decisive evidence, not the count.
- **Determinism claims: rerun twice + json-diff.** For "deterministic fingerprint
  byte-identical; timings environment-sensitive": run twice and diff. This pass:
  only `sizes[*]/observations[*]/value` (wall-clock ms) differed across reruns —
  counts/gates/payloads byte-identical, exactly matching the doc's own env-sensitive
  carve-out (D-32) → PASS. Script `_fingerprint()` hashes "deterministic sections
  only".
- **Typed-annotation regex traps**: `REQUIRED_SIZES` is a tuple-of-tuples
  (`((30, 50), (75, 150), ...)`) — a `\[[^\]]*\]` list regex misses it;
  `EXACT_SOURCE_IDS: frozenset[str] = frozenset({...})` defeats
  `(?:frozenset|set)?\s*[\({]` because `[str]` sits between `:` and `=`. Anchor on
  the annotated assignment (`cv.find("EXACT_SOURCE_IDS: frozenset[str]")`) then
  regex the `frozenset({...})` block; count quoted ids = 98.
- **Dated-count adjudication re-confirmed**: "14 passed" PASSes as history —
  `git show 4903b23:spoilerless/tests/test_visualization_baseline.py | grep -c 'def test_'`
  = 14 (live 15); `-k "variant or bound"` still matches exactly 7 live test names.
- **Fixture sub-claims: grep, don't trust prose**: KNOWS edges carry
  `origin: "user"` in both fixtures (doc's "KNOWS 1 (user)"); E02 omitted edges =
  exactly the 6 `OCCURRED_IN` ids + `edge_12` (WORKS_WITH char_maria_laguerta →
  loc_miami_metro, a Location endpoint) — asserted verbatim in both variant tests.

## project-spec.md verify pass (2026-08-14) — planning/spec doc adjudication

`docs/architecture/project-spec.md` verified 53/56. Planning/spec docs carry a
status vocabulary ("**implemented**" vs "prototype target" vs "future direction"):
only **implemented** sentences are claims; normative invariant text (must/should,
ontology restated as requirements, §9/§10 future/historical sections) is NOT
checkable — skip it, don't fail it. Reusable verdicts from this pass:

- **RETRIEVAL-GATING FACT (supersedes every "lookups don't gate the Claim" claim):**
  all four retrieval evidence/source lookups — `GET_EVIDENCE_QUERY`,
  `GET_SOURCES_QUERY`, `EVIDENCE_FOR_CLAIMS_QUERY`, `SOURCES_FOR_CLAIMS_QUERY` in
  `spoilerless/app/retrieval/tools.py` — include `visible_claim_where()`, which
  gates the matched Claim's own `visible_from_order`, origin allowlist,
  `claim_type`, AND validity window. Any doc saying these lookups "gate the
  relationship/node but not the matched Claim" (project-spec §3.2 line ~111 and
  §7 line ~211) is STALE → FAIL each occurrence. The PROB-09/#62 hotspot now runs
  at every claim-selecting site (1 def, 7 call sites).
- **ROADMAP.md anchor trap:** ROADMAP.md has NO numbered subsections (### headings
  are unnumbered). Any "ROADMAP.md §X.Y" citation is a dead anchor → FAIL with
  actual = "no §X.Y anywhere in docs/ROADMAP.md" (project-spec's §8.6 ref failed
  this way).
- Passed-and-reusable fact bank (project-spec):
  - 52 ops / 39 templates locked by `test_frontend_contract_doc.py`: asserts
    `len(documented) == len(generated) == 52` and `len(EXPECTED_TEMPLATES) == 39`.
  - `VisualizationView` Literal = exactly 6 (episode_overview, character_network,
    plot_threads, investigation, full, graphrag_focus); `ExpansionKey` Literal =
    exactly 7 (family, work, conflict, episode_events, clues, locations, evidence);
    `EXPANSION_DEFAULT_LIMIT = 12`, `EXPANSION_MAX_LIMIT = 25`; expand `limit`
    Query `ge=1 le=25`; expand route deliberately never cached (T10-CACHE-06).
  - `GraphResponse` = series, visible_until_order, effective_view_order, nodes,
    edges, claims, sources, evidence + model_validator `enforce_graph_closure`
    (dangling-edge ValueError).
  - `llm_enabled: bool = Field(default=False)` → "chat disabled unless configured".
  - candidates router prefix `/api/series/{series_id}/candidates`; BOTH
    `list_candidates` and `get_candidate` call `_require_resolved_boundary`
    (422 INVALID_REQUEST envelope on omitted/nonpersisted order).
  - revision actions Created/Updated/Deleted/Reverted in `domain/revision.py`;
    `audit_visibility_integrity` in `graph/seed.py` runs inside `setup_database`;
    `validate_seed` raises "Claim evidence is missing" for claims without
    evidence_ids/source_id.
  - deterministic candidate IDs = `hashlib.sha256` in
    `spoilerless/app/graph/candidates.py` ("Derive deterministic candidate ID from
    payload content (D-11)").
  - citation validation in `retrieval/pipeline.py` `_citation_survives(raw,
    retrieved)` — survives iff every referenced ID was retrieved this turn.
  - `@app.get("/health")` calls `database.verify_connection()` → 503
    "degraded"/"unavailable" on failure (never hard-coded connected).
  - origin strings in `spoilerless/app` are ONLY canonical/candidate/user; no
    curated/automatic/is_custom anywhere; OCCURED_IN appears nowhere in code
    (only inside the doc's own prohibition sentence — count that as PASS).

## spoiler-threat-model.md verify pass (2026-08-14) — 73/101, 28 failures

`docs/architecture/spoiler-threat-model.md` (dated 08-03) drifted hard. Live truths
to reuse (re-verify each pass; baseline `.planning/tmp/verify-spoiler-threat-model.md.json`):
- **P3 share clamping is IMPLEMENTED, not Desired**: `api/share.py:56-67` (CR-01) clamps
  requested → `min(requested, view_as_of_order)` → `effective_view_order(view, watched)`;
  no progress fails closed to 1. Test `test_share_api_create_clamps_boundary_to_creator_progress`
  exists. Doc's "stored boundary not clamped" + matrix "clamp DESIRED" are stale.
- **Rate limiter is fully fail-open now** (PROB-23): `RedisBucket.init()` inside
  `init_rate_limiter()` (rate_limit.py:131-148) and `limiter.try_acquire_async` (92-103)
  are BOTH wrapped → degrade to no-op, never 500. Doc's "not fully fail-open" stale.
  (SUPERSEDED by the FIX iteration-2 pass: `test_rate_limit.py` now has 8 tests incl.
  `test_redis_outage_degrades_to_noop_not_500` :99 and `test_init_rate_limiter_degrades_on_redis_failure`
  :131 — the fail-open degradation IS covered; the old "tests only identifier/429-callback
  pure functions, no propagation test" note is stale.)
- **reject_change_set is NOT admin-gated** (api/change_set.py:134, CurrentUser only);
  confirm IS (line 95, RequireAdminDependency). Code comment: "propose/reject/revert are
  intentionally NOT gated". Doc's "confirm/reject are admin-gated" (lines 28, 118) false.
- **Tool registry** (pipeline.py:441 `TOOL_SPECS`, 12 tools): read tools =
  search_entities, get_entity, get_neighborhood, find_path, get_timeline,
  get_character_context, get_claims, get_evidence, get_sources,
  get_current_visible_graph_summary, get_user_notes + propose_changeset (12th).
  `fetch_episode_codes` (tools.py:510) is an internal helper, NOT registered — doc's
  "11 read tools incl. fetch_episode_codes" stale. `$visible_until_order` literal count
  in tools.py = 27 (doc said 39).
- **characters.json (32 rows)**: 6 characters carry BOTH `image_url` AND
  `image_source_url` (all visible_from_order:1) — phase-10 added `static/characters/*.webp`.
  Doc's "0 image_url / 6 image_source_url only" stale.
- **P1 path route**: boundary resolves from persisted progress alone, "never from the
  MAX_PATH_HOPS hop constant" (api/graph.py:484-487, PROB-09/#59). Doc's "MAX_PATH_HOPS
  (4) as the server-injected requested order" stale (max_hops param IS client-supplied 1..4).
- **No `RESOURCE_NOT_FOUND` literal in api/user_content.py** (doc cited :39, now a route
  summary; 404s declared via `error_responses` only). progress.py has it at 69,106,108.
- **Retrieval gating + contract numbers**: see project-spec pass above — the four
  retrieval lookups gate the matched Claim via `visible_claim_where()` (G4/G5/I15
  "only partial" claims FAIL), and `test_frontend_contract_doc.py` locks 39 templates /
  52 ops while `test_openapi_contract.py` pins `len(schema["paths"]) == 39` (doc's
  "37/50" and "still pins 32" both stale).
- **Test files rewritten since 08-03 — VERIFIER FALSE-NEGATIVE CORRECTION (08-14, re-grep confirmed):** the 08-14 first-pass verifier claimed `test_retrieval_tools.py` = 4 tests and `test_citations.py` = 1 test and that ALL doc test-name claims + `-k` selectors match NOTHING at HEAD — that was a FALSE NEGATIVE (the verifier read only the file head; `grep -c "def test_"` shows **40** and **8**). Live: test_get_evidence_visible_only, test_get_sources_visible_only, test_find_path_* exist in test_retrieval_tools.py; test_hidden_claim_evidence_source_citations_are_rejected exists in test_citations.py; test_graph_api.py has both image tests. The doc's test citations and matrix selectors were CORRECT and the fix agent correctly left them untouched. RULE: when a verifier flags test-name/selector claims, `grep -c "def test_"` (or `async def test_`) the test file YOURSELF before dispatching a fix; re-verify prompts must say "verify test-name claims by listing the actual test files".
- Verified EXACT line refs that still hold: services/chat.py:226,237,278;
  services/graph.py:51,92; domain/chat.py:71,102; domain/change_set.py:274;
  domain/series.py:24; services/series.py:52-55; useWatchProgress.ts:41 (STORAGE_KEY);
  EpisodeSelector.tsx:25,61-62,85 (file moved to `components/episode/`).

## New traps from the spoiler-threat-model pass (generalize to any doc verify)
- **Matrix rows cite `-k <substring>` selectors — verify the selector MATCHES a live
  test name, not just that the test FILE exists.** After test rewrites, `-k "claim"` on a
  small file can match zero tests while the row still says IMPLEMENTED (hit on G3/G4/G5/
  C2/S1/S3/L2/T2/P1 rows).
- **Threat-model "Desired"/"unmitigated" claims are prime drift candidates**: re-check
  every "not"/"Desired" claim against code AND code comments (the confirm docstring
  "intentionally NOT gated" disproved the admin-gating claim). The P3 clamp and the
  rate-limiter were both FIXED after the doc's date — this is the assignment's
  "absence claims honest" focus.
- **Data-file claims drift with seed changes**: characters.json image_url counts changed
  when phase-10 added images — json.loads + Counter the live file, never trust doc prose.
- **Registry-composition claims**: verify "N tools / list of X" against the live registry
  (`TOOL_SPECS` names), not the doc's list — helpers silently drop out of registration.
- **Count claims**: "39 literal occurrences" → count the literal in the file; refactors
  drift counts (27 live).

### spoiler-threat-model.md FIX iteration 2 (doc-writer, 32/32) — rules that generalize to any fix pass

Cleared all 32 (28 stale pins + 4 content) with Edit-only surgery. Lessons:

- **Verifier dedupes identical claim strings doc-wide**: a stale pin is reported ONCE, at the
  first line containing it; the same pin text on other lines goes UNFLAGGED (hit this pass:
  `(filter.py:86)` on the G3 Claim row, `(tools.py:239)` on I11, `(domain/graph.py:50)` +
  `(spoiler/filter.py:153)` on I16, `(retrieval/tools.py:519)` + `tools.py:47` on the P1 row —
  all same pins as flagged lines L61/L86/L64/L103). In fix mode — ESPECIALLY the last allowed
  iteration — fix every occurrence of each flagged pin string: `replace_all=true` on the bare
  pin substring (e.g. `tools.py:239)` → `tools.py:240)`) is the surgical way. A re-verify that
  checks per-line would otherwise re-flag the duplicates.
- **Query "defs" are module-level assignments, not `def` statements**: `NODES_QUERY = """..."""`,
  `VISIBLE_CLAIMS_QUERY = (...)`. A `^\s*def\s+NAME` regex returns NOT FOUND on them. Match
  `^\s*NAME\s*(?::[^=]+)?=`. Same for constants (`_MAX_TOOL_RESULT_CHARS = 4000`,
  pipeline.py:105) — verifier-speak "def at :105" just means "symbol/assignment at :105".
- **Patch-tool transient no-match on a provably-present string**: `(main.py:188-201)` failed
  twice with "Could not find a match" while `text.count("main.py:188") == 1` confirmed it was
  there; a third attempt with a WIDER old_string (`headers, main.py:188-201)`) succeeded.
  When a patch fails on a string that provably exists, widen the context — do not retry
  identically (also dodges the repeated-exact-failure loop warning). Suspect: concurrent
  same-file patches in one batch race the read-modify-write; serializing same-file patches
  is the safe default.
- **"covers only X" test-coverage claims drift**: "test_rate_limit.py covers only the
  identifier/429-callback pure functions" was stale — live has 8 tests incl.
  `test_redis_outage_degrades_to_noop_not_500` (:99) and `test_init_rate_limiter_degrades_on_redis_failure`
  (:131) proving the fail-open degradation. `grep -c "def test_"` the file before trusting
  any coverage-scope claim.
- **"no test named X exists" absence claims**: re-check against the FULL test file —
  `test_baseline_latency_payload_and_layout_inputs` (test_visualization_baseline.py:484)
  disproved "no test named `layout` exists at HEAD". Same rule as the 08-14 false-negative
  correction: list `def test_` across the whole file, never the head.

Corrected pin map for this doc (re-verify anchor, all confirmed live this pass):
`_resolve_effective_boundary` api/graph.py:397 (calls 226,349,488,521; progress deps 53,86);
filter.py NODES_QUERY 89, VISIBLE_CLAIMS_QUERY 127, STRUCTURAL_EDGES_QUERY 106,
VISIBLE_USER_RELATIONSHIPS_QUERY 168, EVIDENCE_QUERY 221, SOURCES_QUERY 193,
SERIES_EPISODES_QUERY 58 (title fields 68-69, synopsis 70); tools.py GET_CLAIMS_QUERY 170,
CLAIMS_FOR_FRONTIER_QUERY 48, SEARCH_ENTITIES_QUERY 136, search_entities 522, find_path 565,
GRAPH_SUMMARY_COUNTS_QUERY 240, get_current_visible_graph_summary 775, GET_EVIDENCE_QUERY 191
(visible_claim_where compose 196); policy.py is_visible 86, effective_view_order 100,
require_visible_resource 158, assert_visibility_invariants 239, mask_episode_metadata 203;
cache/graph_cache.py 75/95/115; domain/graph.py GraphSource 54 (locator 59); repository/chat.py
snapshot 122/141; domain/chat.py title 103 (api/chat.py import 27, use 64);
repository/change_set.py ChangeSetStale 79; `_SENTINEL_SPECS` api/exceptions.py:62-67 maps
ChangeSetStale→409 CHANGESET_STALE; confirm route api/change_set.py:78-113; IVUO progress.py
67/110 + graph.py 129/204; export route api/graph.py:502-560 (render 531/556, Content-Disposition
536, default 512); main.py header dict 47-59 (middleware reg 215), CORSMiddleware 198-214
(X-LLM headers 209-212); tools.py ceilings at 27,30,31,32.

## UAT golden-path record pass (2026-08-14) — historical-record adjudication

`docs/uat/phase-10-golden-path.md` verified 26/27 (1 FAIL: "App.test.tsx four-tab suite
(34 tests)") — CLOSED by the iteration-2 re-verify below (28/28 after the 34→32 fix).
Rules that generalize to ANY UAT/checklist record:

- **UAT outcome rows are historical records**: `✅ PASS` rows framed with a Date +
  operator-hands-on evidence pass as-is. What IS checkable per row: file/test existence,
  feature wiring vs shipped code (projection literals, endpoints, quick-task IDs), seed
  data (data/dexter/metadata/episodes.json codes S01E01–S01E03), and the row/backstop
  structure (UI-* identifiers).
- **Count parentheticals in evidence cells are checkable, not history**: verify test
  counts at the DOC-DATE commit, not just HEAD. Read-only technique, no checkout:
  `git ls-tree -r --name-only <commit> <subdir>` filtered to `*.test.ts*`, then
  `git show <commit>:<path>` per file, count with `\b(?:it|test)\.?(?:each|concurrent)?\(`.
  Results: "392-test full frontend suite" == EXACTLY 392 at session-end commit 316b938
  (08-13 23:54) → PASS as history; "34 tests" was NEVER true in git history (28 at
  doc-plan commit ac27a43, 31 at HEAD b133ee7) → FAIL the count parenthetical, keep the row.
- **Count-method sanity check**: live per-file count should land near a documented vitest
  total (404/44 on 08-14; the `git show`-based count gave 400 — ±4 tolerance from it.each
  row expansions / non-`.test.` files). Small consistent delta ⇒ method sound.
- **Regex trap**: `\b(?:it|test)\.(?:each)?\(` (dot-first) silently returns 0 everywhere —
  `it(` has no dot. Always write `\.?`.
- **Wiring claims: component and suite are SEPARATE evidence**: App.test.tsx's 260814-viz
  wiring describe covers character_network / expand / graphrag_focus but NOT `investigation`;
  the Evidence-tab fetch is wired in App.tsx's mode map (`'evidence' → 'investigation'`,
  answer_graph → `'graphrag_focus'`) and covered by GraphCanvas.test.tsx (investigation
  dagre routing, D-25) + useSceneState.test.ts (SET_VIEW / OPEN_TEMPORARY / CLOSE_TEMPORARY).
  A missing test citation does NOT falsify a wiring claim — check the component first.
- **Backstop UI-* identifiers: grep repo-wide, not just the decision log**: only 4/7
  (UI-RESP-01, UI-GESTURE-01, UI-A11Y-01, UI-DENSE-01) appear in
  `docs/decision-logs/phase-10-visualization.md`; UI-TEXT-01 / UI-IMAGE-01 / UI-RESTORE-01
  live in `.planning/milestones/v1.3-phases/10-polish-finishing-touches/{10-04,10-05,10-07,
  10-10}-{PLAN,SUMMARY}.md`, `10-VERIFICATION.md`, `docs/uat/phase-10-screenshots/README.md`.
  All 7 traceable → PASS.
- **Quick-task IDs**: 260813-wyp has a `.planning/quick/260813-wyp-*/` dir; 260813-fil does
  NOT (only STATE.md / 10-10-SUMMARY refs) — traceable either way; the decisive check is
  the shipped artifact (GraphFilterPanel.test.tsx, exactly 5 tests).
- **Absence claims**: "no screenshots were taken" verified by `docs/uat/phase-10-screenshots/`
  containing only README.md (no image files).
- **GAP-1** (audit-gap reference in UAT rows 8/9): documented in
  `.planning/{MILESTONES,PROJECT,RETROSPECTIVE,STATE}.md` + `v1.3-MILESTONE-AUDIT.md`,
  NOT in the decision log — grep the whole repo before failing.
- **Backend evidence in UAT rows**: "chat-llm chunk green on FakeLLM (10-09 full gate)" —
  chunk names live in `scripts/run_backend_tests.py` `CHUNKS` dict (NOT
  run_phase10_backend_tests.py, which delegates via CHUNK_RUNNER); "10-09 full gate" =
  `10-09-SUMMARY.md` recording "11/11 chunks green (... chat-llm ...)". Grep the CHUNKS
  dict before failing a chunk-name claim.
- **Artifact write pattern**: role mandates the Write tool; conventions mandate
  generate-via-script — write with write_file, then re-parse+assert the written file
  (doc_path verbatim, passed+failed==checked, len(failures)==claims_failed, failure shape)
  in a follow-up execute_code. Satisfies both rules.

## frontend-api-contract.md verify pass (2026-08-16) — 71/73, TWO live BLOCKERs

`docs/reference/frontend-api-contract.md` verified 71/73 PASS. Baseline artifact:
`.planning/tmp/verify-frontend-api-contract.md.json`. Re-verify these two if the doc
claims to be fixed:

1. **CSRF section (~line 162) is STALE — BLOCKER.** Doc: origin verification attached
   only to google/logout; "progress, chat, ChangeSet, settings, and other state-changing
   route families do not apply it... current CSRF limitation." LIVE: `CsrfGuardDependency`
   (= `Annotated[None, Depends(verify_origin)]`, deps.py:210) is wired into EVERY
   state-changing route — candidates ingest/approve/reject/edit, change-set
   propose/confirm/reject/revert, chat create/delete session + messages/stream, progress
   POST, revisions revert, settings PUT llm, share create/revoke, all user_content writes.
   Only GETs are guard-free. Per-route signature scan is decisive here (see type-alias
   bullet above — a Depends-only scan would have "confirmed" the doc).
2. **Candidate-422 interpolation (~line 76) is STALE — BLOCKER.** Doc: "candidate
   ingest/approve/reject/edit paths currently interpolate caught exception text into
   public 422 messages." LIVE: PROB-09/#71 removed the catch-all — ingest/approve/reject
   raise/propagate with no `str(exc)` (comments at api/candidates.py:137-141, 237-240,
   273); only edit_candidate maps ValueError → 422 INVALID_EXTRACTION_PAYLOAD with
   str(exc) (318-319). Re-checked per the known-bug rule: fixes land without doc updates.

Reusable fact bank (re-derived this pass — reuse, don't re-derive):
- Inventory: doc table 52 ops/39 templates == `EXPECTED_OPERATIONS` in
  `tests/test_frontend_contract_doc.py` (asserts `len(documented)==len(generated)==52`,
  `len(EXPECTED_TEMPLATES)==39`, doc == generated openapi). Live routers contribute 51
  ops; `GET /health` lives in main.py — the GET IS in openapi (typed 503 responses);
  only `HEAD /health` is the hidden `include_in_schema=False` one.
- **DTOs live in `spoilerless/app/domain/*.py` — there is NO `app/schemas/` directory**
  (task briefs saying "schemas/domain" mean domain/). File names mirror the old schema
  names (auth.py, chat.py, change_set.py, ...). Glob for schemas/ returns empty → that's
  a wrong-path assumption, not a tool failure.
- Config cookie defaults (core/config.py): session_cookie_name="session",
  session_ttl_seconds=604800, session_cookie_samesite="lax", session_cookie_secure=True,
  frontend_origins="http://localhost:5173".
- Error envelope: `http_error` in core/errors.py → `HTTPException(detail={"code","message"})`;
  `_SENTINEL_SPECS` (api/exceptions.py:44-69) maps UserContentConflict→409
  RESOURCE_CONFLICT, ChangeSetStale→409 CHANGESET_STALE, ChangeSetRevertUnsupported→422
  INVALID_REQUEST, ConcurrentGenerationLimitExceeded→429 TOO_MANY_REQUESTS.
- Enums (domain/): Origin={canonical,candidate,user}; NoteTargetType={Character,Claim};
  CustomNodeType=5; CustomRelationshipType=16 predicates; MessageStatus=
  {pending,completed,failed}; RevisionAction={Created,Updated,Deleted,Reverted};
  ChangeSet = 13 operation_type Literals. graph.py: VisualizationView=6, ExpansionKey=7;
  visualization.py EXPANSION_DEFAULT_LIMIT=12 / EXPANSION_MAX_LIMIT=25; expand route
  deliberately cache-free (graph.py:358 "Deliberately NO cache-aside here (T10-CACHE-06)").
- Chat sessions list: `CHAT_SESSION_LIST_QUERY` in app/graph/chat.py =
  `ORDER BY session.updated_at DESC, session.id` (deterministic, newest first).
- Note-filter pairing IS enforced: repository/user_content.py list_notes raises
  UserContentValidationError (→422 INVALID_REQUEST) when `(target_type is None) != (target_id is None)`.
- frontend/src/types/userContent.ts still stale (node_type instead of backend `type`;
  NoteResponse/CustomNodeResponse lack user_id) — doc ~line 204 accurate as of 08-16.
- "reject_change_set is NOT admin-gated (CurrentUser only)" (see spoiler-threat-model
  pass) still holds — the doc's admin-gate list (approve/reject/edit, confirm, LLM
  settings) does NOT claim reject is admin-gated, so it passes.

### frontend-api-contract.md iteration-2 re-verify (2026-08-16+) — 81/81 PASS, both BLOCKERs closed

Full fresh re-verify after the two surgical fixes; both prior BLOCKERs confirmed FIXED in live code
(`.planning/tmp/verify-frontend-api-contract.md.json` overwritten; fresh tally 81 vs first-pass 73 —
honest fresh extraction, ARCHITECTURE 276→533 precedent):

- **CSRF scope FIXED**: per-route signature scan (type-alias variant — `_csrf: CsrfGuardDependency`)
  shows `CsrfGuardDependency` on ALL 26 state-changing routes + auth google/logout: candidates
  ingest/approve/reject/edit, change_set propose/confirm/reject/revert, chat sessions POST/DELETE +
  messages/stream, progress POST, revisions revert, settings PUT llm, share POST/DELETE, all 9
  user_content writes. **The ONLY non-GET without the guard is the read-only `POST /graph/path`
  (`find_shortest_path`, api/graph.py — allowlisted find_path executor, server-injected params,
  PROB-09/#59)**. The doc's "Only read-only GET routes skip it" PASSES — the checkable assertion is
  the state-changing enumeration, which is exact; don't false-FAIL on the graph/path POST.
- **Candidate-422 interpolation FIXED**: `str(exc)` survives ONLY inside comments (candidates.py:141,240 —
  ingest/approve "never interpolated"); the sole live raise is edit_candidate :318-319
  `raise http_error(422, "INVALID_EXTRACTION_PAYLOAD", str(exc))`. INVALID_EXTRACTION_PAYLOAD appears
  at :115 (error_responses decl) and :319.

New/refreshed facts (extend the fact bank above; re-verify each pass):
- `ERROR_CODES` frozenset lives in **`spoilerless/app/core/errors.py` (32 codes)** — NOT
  api/exceptions.py (grep the whole app tree; the `frozenset[...]`-block trap applies wherever it is).
- Full `_SENTINEL_SPECS` mapping (api/exceptions.py, registered via
  `install_repository_error_handlers(app)`): UserContentNotFound/ChangeSetNotFound/
  ChangeSetSessionNotFound/ChatSessionNotFound/ProgressNotFoundError → 404 RESOURCE_NOT_FOUND;
  UserContentValidationError/ChangeSetValidationError/ChangeSetOperationInvalid/
  ChangeSetRevertUnsupported → 422 INVALID_REQUEST; UserContentConflict → 409 RESOURCE_CONFLICT;
  UserContentForbidden → 403 FORBIDDEN; ChangeSetStale → 409 CHANGESET_STALE;
  ConcurrentGenerationLimitExceeded → 429 TOO_MANY_REQUESTS.
- Decisive fast inventory evidence for THIS doc: `unset PYTHONPATH && uv run python -m pytest
  spoilerless/tests/test_frontend_contract_doc.py -q` → 3 passed in 0.79s (asserts
  documented==generated==EXPECTED_OPERATIONS, len 52/39, openapi paths == templates) — beats manual
  route counting and the full suite.
- propose_change_set rejects `payload.series_id != series_id` with 422 INVALID_REQUEST before the
  service call (doc's "rejects it unless it equals the path series_id").
- Note-substitution for canonical/candidate Character|Claim lives in **services/change_set.py**
  (`_override_note_content`, "honest create_note-shaped override proposal").
- share revoke: `return {"status": "revoked"}` with NO status_code — the doc's "200 revoked" is the
  DEFAULT status, not a declared one.
- Backend CustomNodeResponse exact fields = id, series_id, user_id, type, label, visible_from_order,
  origin, episode_id, created_at, updated_at (field `type`, NOT node_type); GraphEvidence.content_hash
  is `str | None` (nullable). frontend/src/types/userContent.ts STILL stale (CustomNodeResponse uses
  node_type, no user_id in any response type) — doc's staleness claim accurate.

## frontend-components.md verify pass (2026-08-14) — 187/189, 2 failures

`docs/reference/frontend-components.md` (snapshot 08-13) verified 187/189. Fact bank:
`references/08-14-frontend-components-doc-facts.md`; baseline
`.planning/tmp/verify-frontend-components.md.json`. Failures: (1) L183 `graphStylesheet`
identifier does not exist (graphStylesheet.ts exports only `buildGraphStylesheet`); (2) L294
"current integration note" is STALE — App.tsx DOES pass `readOnly={isVisitor}` to DetailPanel
(code moved; doc didn't). Component-reference traps that generalize to ANY `frontend/src` doc:

- **Named-export claims: grep the whole src tree** — the documented component may live in a
  differently-named file (GraphLoadingState/GraphErrorState/GraphEmptyState are exports of
  GraphStatus.tsx, not separate files). Never conclude "missing" from the implied filename alone.
- **Prop-name adjudication**: a doc identifier may name the App-level wiring prop rather than
  the component's own prop (doc "clears through onClearFocus" — App/GraphCanvas prop is
  `onClearFocus`, GraphFocusIndicator's prop is `onClear`). PASS when the identifier exists
  anywhere in the flow; FAIL only when it exists nowhere.
- **Alias-aware signature claims**: doc diagram `useGraph(seriesId, confirmedOrder)` vs live
  `useGraph(watchProgress.seriesId, watchProgress.viewAsOfOrder)` — PASS because the doc itself
  defines `confirmedOrder` as the alias of `viewAsOfOrder` (useWatchProgress.ts
  `confirmedOrder: state.viewAsOfOrder`). Check the doc's own definitions BEFORE failing a
  call-signature claim.
- **"Current integration note" claims are drift magnets**: any sentence asserting what current
  App wiring does NOT do ("the App.tsx call does not pass X") must be re-checked every pass —
  same rule as known-bug claims. The L294 readOnly={isVisitor} note went stale between the
  doc's 08-13 snapshot and the 08-14 pass.
- **Doc-snapshot headers date the doc, not the wiring**: this doc's header says "Snapshot
  (2026-08-13)... not regenerated automatically" — the snapshot framing does NOT excuse stale
  claims; every checkable claim still resolves against HEAD.
- **Batch-script harness self-check**: mass "failures" from one verify script are usually
  harness bugs (string passed where a compiled pattern was expected; a bool wrapped as a
  callable). Re-check the harness before adjudicating any claim as FAIL — 10 of 14 initial
  batch-1 "fails" this pass were harness artifacts.

## ARCHITECTURE.md re-verify pass (2026-08-14) — 533/533 fresh (prior baseline 276/276)

Re-verify after the Season/Scene surgical fix; the fix holds (no Season/Scene anywhere in
`spoilerless/app/` or `seed.py`). Baseline artifact: `.planning/tmp/verify-ARCHITECTURE.md.json`
(now 533/533). Reusable facts from this pass:

- **NODE_LABELS = 12 labels and `Revision` is the 12th** (Series, Episode, Character, Event,
  Location, Organization, Object, Claim, Source, EvidenceFragment, UserNote, Revision).
  The §4.5 table rows Structural(2)+Narrative(5)+Knowledge(3)+User(1)+`Revision`(System) must
  total 12 or the doc undercounts; STORY_LABELS = 8 (Character, Event, Location, Organization,
  Object, Claim, EvidenceFragment, Source).
- **Relationship inventory**: `ontology/relation_types.yaml` holds 27 types (Structural 4 +
  Participation 6 + Character 10 + Provenance 4 + Revision 3); the 9 System/application types
  (HAS_SESSION..CREATED_SHARE) exist only in code/seed. Count 27 + 9, never 36 in the YAML.
- **BOUNDARY_QUERY usage sites** (grep: filter.py 1 def; services/graph.py 2;
  repository/user_content.py 2, imported as `BOUNDARY_VALIDATION_QUERY`; tests 1). It does NOT
  appear in api/candidates.py or api/share.py — those go through `GraphService.resolve_boundary()`.
  Don't fail "shared with candidate reads and share creation" on a direct-literal grep.
- **Custom-relationship boundary**: the max-of(source,target,episode) rule is an inline Cypher
  CASE in `CUSTOM_RELATIONSHIP_CREATE_QUERY` (repository/user_content.py), NOT
  `derive_visible_from_order` (that serves custom nodes at user_content.py:481 and ChangeSet ops
  at change_set.py:590; signature `(episode_order, current_progress)` → max, fail-closed ≥ 1).
  Doc phrasing "through the shared spoiler/visibility.py rule" is loose attribution; the
  substance (max of three orders) is in the query → PASS.
- **fetch_graph's seven query constants (SERIES_QUERY..EVIDENCE_QUERY) live in
  `services/graph.py`**, not `graph/graph.py` (which doesn't exist). `claim_id` has only 1
  occurrence in services/graph.py (`claim_id=claim.id`) — that's the edge assembly, not drift.
- **graph/chat.py contains NO `visible_from_order` literal** — chat visibility gating is
  `visible_until_order_snapshot <= boundary` (repository/chat.py). "Visibility-gated Cypher
  lives in graph/chat.py" passes on the snapshot mechanism.
- **vllm/ollama scaffolding selectors live in `services/chat.py` `get_llm_provider`**
  docstring/comments, not llm/provider.py — grep chat.py for "scaffolding".
- **Share TTL default 2592000** (30 days) is `create(..., ttl_seconds: int = 2592000)` in
  repository/share.py; `_generate_token()` = `generate_token(32)` (secrets.token_urlsafe).
- **`install_llm_error_handlers` is defined in `llm/provider.py`** (used by main.py), not
  core/errors.py — errors.py has only install_error_handlers/install_database_error_handlers.
- SESSION_SWEEP_INTERVAL_SECONDS = 3600; HealthResponse = status/database/service; security
  headers are a `_SECURITY_HEADERS` dict (CSP default-src 'self' + https://accounts.google.com,
  HSTS, nosniff, X-Frame-Options DENY, Referrer-Policy strict-origin-when-cross-origin).

## New batch-harness traps (generalize to ANY doc verify)

- **`lstrip("./")` eats hidden-file dots**: `.env.example`.lstrip("./") → "env.example", a
  spurious FAIL for a file that verifiably exists. Use `removeprefix("./")` (or
  `re.sub(r'^\./+', '', c)`) for path normalization.
- **Path-existence checks must cover directories AND bare relative names.** A file-only index
  fails every dir claim (`spoilerless/app/api/`, `ontology/`, `data/dexter/`) and every bare
  subdir-relative name (`core/tokens.py`, `lib/graph/highlight.ts`, `node_types.yaml`) — 69 of
  69 "failures" this pass were that harness artifact. Resolve with a multi-root recursive
  basename search: try the claim as-is, then `frontend/src/<c>`, `spoilerless/app/<c>`,
  `spoilerless/<c>`, `spoilerless/scripts/<c>`, `scripts/<c>`, `ontology/<c>` (rglob), and
  check directories too.
- **Fresh re-verify counts legitimately differ from baseline artifacts**: ARCHITECTURE.md
  re-extracted to 533 per-line instances vs the 276 baseline (same claim on multiple lines
  counts per line). Don't force-match the baseline count; report the honest fresh tally.

## PROBLEMS.md ledger re-verify pass (2026-08-14) — LEDGER SEMANTICS in re-verify mode

First pass: 97 checked / 86 passed / 11 failed. Re-verify after surgical fixes:
97/97, failures []. PROBLEMS.md is a numbered-pass LEDGER — the parent names the
LIVE vs HISTORICAL split explicitly; trust it, don't re-derive it:
- 2 LIVE, fixed before re-verify: #8 RESOLVED banner `.env.example` pin 10→16 (content
  at the old pin was false at HEAD — line 10 is now a VITE_* comment); #60 FIXED record
  gained "The revert path still omits `invalidate_series` (known bug, cf. DEPLOYMENT.md)".
- 9 HISTORICAL, correctly LEFT (never re-flag in later passes): #25 junk claim, #26 no
  .github, #28 no LICENSE, #30 whitespace keys, #38 security headers, #39 zero
  observability, #79 god-file counts, TWELFTH API.md 50/37, DEPLOYMENT 15-VERIFY — all
  dated entries; code moved after their pass dates.

LEDGER SEMANTICS adjudication rules (re-verify mode):
- RESOLVED-banner statements of CURRENT state ("verified fixed as of ...: X") are LIVE;
  the pre-fix description BELOW the banner is historical audit trail.
- FIXED records' known-bug tails ("still omits X") ARE live — re-check code still
  exhibits them every pass (fixes land without doc updates). This pass: api/revisions.py
  + revisions/__init__.py = 0 `invalidate_series` calls; candidates.py 4 /
  change_set.py 3 / user_content.py 7 — matches the doc's omission note; DEPLOYMENT.md
  cross-ref still says the same.
- "Still open" lists: only the LATEST pass's list is live (SIXTEENTH supersedes
  THIRTEENTH); earlier ones are historical even when they look similar.
- Dated line pins in banners: adjudicate by semantic content + first-pass acceptance,
  not the pin. `core/config.py:34` in the #8 banner is live line 47 (file grew) — PASS
  (default=True holds; first pass accepted it). Flag a pin only when the content AT
  that pin is false at HEAD.
- Re-verify keeps the first-pass inventory count (97) and adjudicates each flag to
  PASS — PROBLEMS.md flags are adjudicated, not re-extracted (contrast the
  ARCHITECTURE.md 276→533 case above where granularity changed).

Batch-evidence traps hit this pass:
- `subprocess.run(["grep", ...])` inside execute_code → WinError 2 on this host (grep
  not on PATH in the sandbox python). Use pure pathlib rglob + regex for repo-wide
  greps (same family as the search_files MSYS-mangling pitfall above).
- `CHUNKS: dict[str, list[str]]` (scripts/run_backend_tests.py) stores filenames as
  list VALUES per chunk, not dict keys — a colon-key regex returns 0. Count all
  `test_*.py` string literals in the file and diff against the disk glob (51/51
  matched; startup gate `assert_chunk_inventory_matches_disk` exists).
- Wide-context regex `.{60}keyword.{80}` silently misses matches near line starts (def
  lines have no 60 chars before them) — extract function bodies by `find("def name")`
  + slice instead.
- Runner existence claims (NINETEENTH PASS): verify structurally — unique name
  `secrets.token_hex(6)`, password `token_hex(16)`, `_free_port()`,
  `FORBIDDEN_CONTAINERS = {spoilerless-neo4j, hdgraf-neo4j}`, `_verify_effective_settings`,
  `_teardown` docstring "verify absence" — never re-run the guarded runner (needs Docker
  daemon); docstring+def evidence suffices for existence claims.
- Guard-test count: 18 tests live in `spoilerless/tests/test_phase10_test_runner.py`
  (NOT test_phase10_coverage_audit.py, 14 tests — same phase-10 prefix, wrong file).
- Verification-evidence response: when the harness asks to verify the changed path on
  a doc-verify task, the changed path IS the JSON artifact — the strict contract
  re-parse+assert (key set, passed+failed==checked, len(failures)==claims_failed,
  failure shape) is the verification; pytest is inapplicable to a read-only doc
  artifact. Say so; never fabricate test output. If the harness still demands pytest
  evidence, run the doc's OWN referenced test file with the project invocation
  (`unset PYTHONPATH && uv run pytest spoilerless/tests/test_visualization_baseline.py -q`
  → 15 passed live) and report the live count — a delta vs the doc's dated count is
  the historical record, not drift. (`hermes verify --json`'s detected recipe calls
  bare `pytest`, which isn't on PATH here; its `test` phase fails for that reason —
  the targeted `uv run` run is the working evidence path.)

## DEVELOPMENT.md re-verify pass (2026-08-14 re-run) — 195/195 PASS after 5 surgical fixes

`docs/DEVELOPMENT.md` verified **195/195** (baseline `.planning/tmp/verify-DEVELOPMENT.md.json`;
first pass was 118/123 with 5 failures, all five surgically fixed). The five fixes and their
live-code ground truth (re-verified this pass — reuse, don't re-derive):

1. **L63 npm omit=dev**: doc frames the machine state as operator-machine observation
   ("this machine's global npm config set omit=dev") + `<!-- VERIFY: ... -->` marker → PASS
   by framing (external state correctly phrased as unverifiable from repo). `npm ci` + lockfile
   existence still checked normally.
2. **L133 lint claim**: "`npm run lint` is configured and is expected to exit successfully
   with no warnings or errors" + VERIFY marker → PASS by framing. eslint.config.js still has
   exactly 3 react-hooks rules at warn (set-state-in-effect, refs, preserve-manual-memoization)
   + test-file `@typescript-eslint/no-explicit-any` at warn + `src/components/ui/**`
   react-refresh exception.
3. **L141 rate limiter fully fail-open**: `services/rate_limit.py` wraps BOTH
   `RedisBucket.init()` (init_rate_limiter) and `limiter.try_acquire_async()` (`__call__`)
   in try/except Exception → logged, degraded, never propagated. **The log strings use
   EM-DASHES**: "init_rate_limiter: Redis unavailable at startup — rate limiting disabled",
   "rate_limit: Redis unavailable — rate limiting disabled for this request". A hyphenated
   grep returns false negatives.
4. **L180 LLM_DISABLED**: `install_llm_error_handlers` in `llm/provider.py` emits
   `"code": "LLM_DISABLED"` (disabled_handler) + `"code": "LLM_PROVIDER_UNAVAILABLE"`
   (unavailable_handler); `LLM_PROVIDER_DISABLED` appears nowhere in `spoilerless/`.
   Provider classes: `OpenAICompatibleProvider` (provider.py:114) + `GeminiProvider`
   (:313, `base_url` default = generativelanguage.googleapis.com → optional, sends
   `x-goog-api-key` header). The vllm/ollama "scaffolding" comment lives in
   `domain/settings.py:17-21` (`LLM_PROVIDERS = ("gemini", "openai_compatible", "vllm",
   "ollama")`); default `openai_compatible` in `core/config.py`. X-LLM-* headers and
   `:AppSetting {key: 'llm'}` resolution in `services/chat.py`.
5. **L227 CONTRIBUTING anchor**: doc links
   `CONTRIBUTING.md#branches-commits-and-the-issue-ledger` — matches live heading
   "## Branches, Commits, and the Issue Ledger" (CONTRIBUTING.md:177, GitHub slug rule).
   Old broken anchor was `#branches-and-commits`.

Other reusable facts from this pass:
- Contract tests: `test_frontend_contract_doc.py` asserts `len(documented)==len(generated)==52`
  + `len(EXPECTED_TEMPLATES)==39`; `test_openapi_contract.py` asserts `len(schema["paths"])==39`
  + a 52-tuple method-set literal (see trap below).
- `.venv` on this host: 94 site-packages entries, NO spoilerless editable/dist-info/pth →
  DEVELOPMENT.md's "checkout not installed as a package by the current uv environment" (L61)
  is TRUE; verify such claims by listing `.venv/Lib/site-packages`, never by assuming.
- "GET /api/series/{series_id}/graph" etc. verified via decorator paths `/{series_id}/graph`,
  `/{series_id}/graph/visualization`, `/{series_id}/graph/expand` in api/graph.py (prefix
  `/api/series`); expand route allowlisted (test comment "allowlisted semantic expansion (D-21)").
- `_require_resolved_boundary` in api/candidates.py has **3** call sites (list + detail + 1).
- Runner exit codes: `raise SystemExit(main())` with `return 2` for forbidden target and
  `return proc.returncode` (pytest 0/1 propagates) — never literal `exit(0)` calls.
- jsdom engines `^22.22.2 || ^24.15.0 || >=26.0.0` (node_modules/jsdom/package.json) + lockfile
  jsdom 30.0.1 both confirmed; ci.yml frontend uses node-version "24".

## New/generalized traps from the DEVELOPMENT.md pass (apply to ANY doc verify)

- **Em-dash in code log strings**: message text may use "—" not "-". Grep the distinctive
  substring around the punctuation ("Redis unavailable"), or copy the string from source.
- **Decorator path carries `/{series_id}`**: api/graph.py routes are `@router.get(\n
  "/{series_id}/graph", ...)` with APIRouter prefix `/api/series`. A regex for `"/graph"`
  right after `@router.get(` FAILS. Match `/{series_id}/graph` (or `[^"]*/graph`).
- **Count claims asserted as explicit set literals**: test_openapi_contract.py pins 52
  operations as a 52-tuple set literal (`assert methods == {...}`) — the digit "52" never
  appears in the file. Count tuples with a regex over the set block; count PER-TUPLE, not
  per-line (multiple tuples share a line; line-count gave 48 vs 52).
- **Stale comments inside otherwise-live tests**: test_openapi_contract.py:150-152 comment
  says "live surface is 51 ops / 38 templates — TWELFTH-PASS docs refreshed" while the
  asserts right below lock 52/39. Adjudicate from asserts, never from the file's comments.
- **"not installed as a package" claims**: check `.venv/Lib/site-packages` for
  editable/dist-info/.pth entries naming the project; a populated site-packages with no
  match CONFIRMS the negative claim (this host: 94 packages, none spoilerless).
- **Milestone archive layout**: `.planning/milestones/` holds per-milestone DIRS
  (v1.3-phases/10-polish-finishing-touches/ containing 10-01-PLAN.md...) AND SIBLING
  `v1.1-REQUIREMENTS.md`-style files (next to `v1.1-phases/`, not inside it). rglob for
  `*REQUIREMENTS*`/`*ROADMAP*` under milestones/ before failing a "per-milestone
  REQUIREMENTS/ROADMAP" claim.
- **Exit-code claims**: verify return-code propagation (`raise SystemExit(main())`,
  `return proc.returncode`, `return 2`), not literal `exit(0)` occurrences.
- **CONFIGURATION.md anchor**: "### Rate limiting & Redis cache" → slug
  `rate-limiting--redis-cache` (works; the doc's `#rate-limiting--redis-cache` links pass).

## runbook.md re-verify pass (2026-08-14) — partial-fix trap + fact bank

`docs/ops/runbook.md` re-verified 68/71 after "3 surgical fixes" (baseline
`.planning/tmp/verify-runbook.md.json`). Two fixes held; one was PARTIAL.

- **Partial-fix trap (generalizes — same claim in prose + table + code-block
  comment):** the "11 chunks" fix updated only the prose (L183 "11 named
  chunks"). The SAME claim stayed stale in the L192 trailing comment
  `# all 10 chunks` inside the powershell fenced block and in the 10-row chunk
  table (missing the `phase10-viz` chunk; `contract-ops` row missing
  `test_phase10_coverage_audit.py`). After any surgical fix, re-verify EVERY
  instance of the fixed claim — a `git show <fix-commit> -- <doc>` diff reveals
  exactly which instances the fix touched (8beb379: container fix originally
  said `hdgrafcehennemi-neo4j`, later corrected to `spoilerless-neo4j`; ROADMAP
  ref was `§8.7` → corrected to `§8 item 7`).
- **Trailing-comment adjudication:** the role's "skip comment lines (#)" rule
  covers comment-ONLY lines. A trailing comment on a command line
  (`cmd   # all 10 chunks`) is a checkable count claim → FAIL when wrong.

Live fact bank (reuse, re-verify each pass):
- `scripts/run_backend_tests.py` CHUNKS = **11 chunks / 51 files, all unique**:
  core, domain-models, series-api, graph, change-set, candidates, auth,
  user-content, chat-llm, contract-ops (6 files incl. test_phase10_coverage_audit.py),
  phase10-viz (test_visualization_baseline/projection/cache/graphrag +
  test_phase10_test_runner). Startup gate `assert_chunk_inventory_matches_disk()`
  fails before any chunk runs if CHUNKS drifted from disk. `--chunk` takes
  index/name/comma-list; `--list` prints the numbered mapping.
- Health tuples (main.py): 200 `{"status":"ok","database":"connected",
  "service":"spoilerless-backend"}` (SERVICE_NAME constant) / 503
  `{"status":"degraded","database":"unavailable",...}`; locked by
  test_main_lifespan.py. Exactly two branches.
- 09-08 startup schema check = `spoilerless/app/graph/setup.py::_check_visibility_schema`:
  Cypher `labels=list(STORY_LABELS)` only → Episode excluded;
  synopsis_visible_from_order/image_visible_from_order NOT validated;
  test_setup_schema_check.py covers pass + fires-on-drift.
- seed.py setup path: `CREATE CONSTRAINT/INDEX ... IF NOT EXISTS`, MERGE
  upserts, DELETE of stale/legacy rels, `audit_visibility_integrity` (fails on
  null visible_from_order; excludes UserSeriesProgress/ChatSession/ChangeSet).
  graph/setup.py has NO dry-run: `async_main` → `setup_database` →
  `_check_visibility_schema` → SystemExit(1) on RuntimeError.
- docker-compose.yml: `container_name: spoilerless-neo4j`,
  `image: neo4j:2026.06.0-community`, no hdgraf-neo4j anywhere. The `aura_*`
  exports (aura_vars/uri/username/password/database) live in
  `scripts/run_phase10_backend_tests.py`, NOT env-local.sh (which exports the
  NEO4J_* vars directly).
- zombie_sweep.py: `--dry-run`/`--execute`; protected uuid
  `ae8a41b7-db96-40e8-b6c2-2e3c69aedb11`; NEO4J_DATABASE default `"neo4j"`;
  `trusted_certificates=TrustCustomCAs(certifi.where())`; tie check guards ONLY
  HAS_PROGRESS/HAS_SESSION/CREATED/REFERS_TO (zero occurrences of
  HAS_CHAT_SESSION/PROPOSED_CHANGE_SET/CREATED_SHARE in the script — the
  documented KNOWN LIMITATION is still live).
- graph_cache.py: key `f"graph:{series_id}:{effective_boundary}:{user_id or 'anon'}"`;
  invalidation `f"graph:{series_id}:*"` + scan_iter; no `spoilerless:` namespace.
- ChatPanel.tsx names ONLY LLM_PROVIDER_UNAVAILABLE literally; LLM_STREAM_FAILED
  is classified via the "any other LLM_-prefixed error → recoverable failed-message
  bubble" branch — don't fail the "classifies both codes" claim on a literal grep.
- ROADMAP.md §8 = "Known gaps and unresolved risks" (numbered list 1-9); item 7 =
  Testing isolation (~line 267). "§8 item 7" is the correct anchor; "§8.7" is dead.

## runbook.md iteration-2 re-verify (2026-08-14) — 78/78 PASS, fixes held + new traps

All 3 partial-fix failures resolved; fresh full pass = 78/78, failures []. Fix
instances were UNCOMMITTED working-tree changes — `git log -- <doc>` showed only the
08-12 commits, but `git status --short -- <doc>` + `git diff -- <doc>` revealed the real
fix diff. For any re-verify after fixes: check the working-tree diff FIRST, never assume
the fix is committed. Confirmed fixed: L183 "11 named chunks", L192 trailing comment
`# all 11 chunks`, L211 contract-ops = 6 files (incl. test_phase10_coverage_audit.py),
L212 NEW row 11 `phase10-viz` (5 files), container `spoilerless-neo4j`, ROADMAP "§8 item 7".

New/extended traps from this pass (reuse, re-verify each pass):
- **CHUNKS regex needs the type annotation**: the dict is declared
  `CHUNKS: dict[str, list[str]] = {` — a regex `CHUNKS\s*[:=]\s*(\{.*?\n\})` returns None.
  Match `CHUNKS\s*:\s*dict\[str,\s*list\[str\]\]\s*=\s*(\{.*?\n\})`, then per-chunk lists
  via `"name"\s*:\s*\[(.*?)\]`.
- **Health tuples are pydantic constructor calls, not JSON literals**: main.py builds
  `HealthResponse(status="ok", database="connected", service=SERVICE_NAME)` (503 variant:
  `status="degraded", database="unavailable"`). Grepping for `"status": "ok"` /
  `"database": "connected"` FAILS. Verify the constructor kwargs + `SERVICE_NAME =
  "spoilerless-backend"`; "exactly two branches" = exactly 2 status= kwargs in the /health
  handler (try/except → 503 JSONResponse, fall-through → 200).
- **`hdgraf-neo4j` is NOT absent repo-wide**: it lives in
  `scripts/run_phase10_backend_tests.py` inside
  `FORBIDDEN_CONTAINERS = {"spoilerless-neo4j", "hdgraf-neo4j"}` — that guard occurrence
  SUPPORTS a doc's "correct container is spoilerless-neo4j, NOT the stale hdgraf-neo4j"
  claim; docker-compose itself has `container_name: spoilerless-neo4j` + `image:
  neo4j:2026.06.0-community`. Absence sweeps must exclude the FORBIDDEN_CONTAINERS guard
  and docs that name it as stale.
- **UptimeRobot appears in main.py** — in the `@app.head("/health",
  include_in_schema=False)` docstring ("HEAD variant of the health check for uptime
  monitors (UptimeRobot etc.)"). A code docstring is NOT a monitor configuration, so "no
  monitor configuration is tracked in the repo" still PASSES.
- **run_phase10_backend_tests.py env facts**: `DATABASE = "neo4j"` constant (backs the
  doc's "scripts default NEO4J_DATABASE to neo4j" plural); `AURA_VARS = ("AURA_URI",
  "AURA_USERNAME", "AURA_PASSWORD", "AURA_DATABASE")` is UPPERCASE — the lowercase
  `aura_vars` literal does not exist (lowercase `aura_uri` etc. appear only as keys in
  connection_map dicts). Grep the uppercase tuple name.
- Chunk table now equals live CHUNKS exactly (11 rows / 51 files / all unique; disk glob
  of spoilerless/tests also = 51, zero drift both ways). Inventory gate
  `assert_chunk_inventory_matches_disk` still present. `--list`/`--chunk` flags + health
  tuples locked by test_main_lifespan.py unchanged.

## feature-ideas.md re-verify pass (2026-08-14) — 80/81; ROADMAP anchor STYLE partial-fix trap

`docs/ideas/feature-ideas.md` re-verified 80/81 after a surgical fix
(`ROADMAP §8.4` → `ROADMAP §8.3`); baseline artifact
`.planning/tmp/verify-feature-ideas.md.json`.

- **Partial-fix trap, STYLE variant (generalizes the runbook §8.7 case):** the
  fix corrected the ITEM NUMBER (§8.4 = Automatic ingestion → §8.3 = Source
  navigation, semantically right) but kept the dead `§X.Y` citation style →
  still FAIL. Repo-canonical form is `§8 item N`: project-spec.md ("ROADMAP.md
  §8 item 6") and runbook.md ("§8 item 7") are the only other ROADMAP-§8
  citations in docs/ — `§8.N` appears nowhere else. When a re-verify names a
  "corrected ROADMAP anchor", verify the STYLE against sibling docs, not just
  the item number. Failure actual used: "no §8.3 anywhere in docs/ROADMAP.md —
  ROADMAP §8 is a numbered list (items 1-9); correct citation 'ROADMAP §8 item 3'".
- **`ChangeSetOperation` is an Annotated-Union type alias, not a class**
  (`class ChangeSetOperation` regex → nothing; it's
  `ChangeSetOperation = Annotated[Union[CreateNodeOperation, ...]]` in
  domain/change_set.py). The type-alias trap family covers MODEL/type claims
  too, not just dependency annotations. Verified via the ChangeSetCard.tsx code
  comment ("the backend's `ChangeSetOperation` payload never carries a 'before'
  snapshot value (confirmed against spoilerless/app/domain/change_set.py)") +
  JSX render `<span>Before:</span> Not shown` — a UI-string claim can pass on
  the code comment + render even when the backend type is alias-shaped.
- **LLM-settings fields live in domain/settings.py, NOT core/config.py** —
  `system_prompt_language: Literal["english", "turkish"] = "english"` is in
  domain/settings.py (cf. LLM_PROVIDERS there too); core/config.py holds base
  settings only. For config-field claims with no cited location, grep the whole
  app tree before failing.
- **Route-param name trap:** candidate approve/reject are
  `POST /{claim_id}/approve` and `/{claim_id}/reject` — a regex assuming
  `{candidate_id}` returns NOT FOUND. Dump decorators
  (`@router\.\w+\(.*?\)\s*(?:async\s+)?def\s+(\w+)`, re.S) instead of guessing
  the param name.
- **Upsert-semantics claims: module docstring is decisive evidence** — the
  UserSeriesProgress MERGE Cypher is regex-resistant, but repository/progress.py
  states it verbatim in its docstring ("The MERGE-based upsert is atomic:
  concurrent updates for the same (user, series) resolve to one row...");
  docstring + `'upsert' in file` + node-label grep suffice.
- **Named-export instance:** `RevisionItem` is defined INSIDE
  RevisionHistoryPanel.tsx (renders `Before: {diff.before}` + `→`); GraphEmptyState
  inside GraphStatus.tsx (already known). Component claims pass via definition
  location, never the implied filename.
- **Fact bank (reuse, re-verify each pass):** find_path + get_character_context
  defined in tools.py and both registered in pipeline.py TOOL_SPECS;
  `POST /api/series/{series_id}/graph/path` route exists (api/graph.py); "Show
  path" in GraphControls.tsx; GraphCanvas props newlyRevealedIds + 4000 ms
  highlight; GraphFilterPanel nodeType + edgeFamily client-side filters;
  NodeSearch/CommandPalette search graph payload + user notes via
  searchIndex.ts ("Zero-dependency substring search index" header comment);
  CitationChip "Show in graph" wired in App.tsx; SessionPicker
  select/create/delete with NO rename; ChatSession.title: str; claim_types.yaml =
  low/medium/high/verified + candidate/corroborated/canonical/disputed/rejected;
  Origin(StrEnum) canonical|candidate|user; no tag field in user_content note
  domain; share repository token + captured-boundary read; GET revisions route
  carries a resource filter; ROADMAP "### Milestone 8" exists with
  "- [ ] Implement a complete human review UI" (API-only workflow); §9 lists
  ingestion, vector/hybrid, appearance counts, multi-user, Kubernetes.

### feature-ideas.md iteration-2 re-verify (2026-08-16) — 75/75 PASS, canonical §8 item 3 fix HOLDS

Full fresh re-verify after the second surgical fix (L33 `ROADMAP §8.3` → `ROADMAP §8 item 3`):
**75/75, `failures: []`** (`.planning/tmp/verify-feature-ideas.md.json` overwritten; fresh tally 75 vs
first-pass 81 — honest fresh extraction, ARCHITECTURE 276→533 precedent). The fix is an UNCOMMITTED
working-tree change — `git diff -- docs/ideas/feature-ideas.md` is the decisive evidence, never `git log`
(runbook iteration-2 rule re-confirmed). ROADMAP §8 = numbered list (items 1-9); item 3 = "Source
navigation: detail UI shows plain-text source metadata/locators, not navigable links" — matches the doc's
claim verbatim; no `§8.N` style remains anywhere in the doc. New harness traps hit this pass:

- **rglob basename collision across spoilerless/app subdirs**: `progress.py` exists in FIVE places
  (api/, domain/, graph/, repository/, services/) — `rglob("progress.py")[0]` landed on api/progress.py
  (the routes file) → false FAIL on the ProgressRepository-merge claim. For claims about a specific class,
  anchor the target subdir explicitly (`repository/progress.py`); never take `hits[0]`.
- **Frontend handler names ≠ generic verbs — literal-substring checks false-FAIL**: SessionPicker.tsx has
  ZERO occurrences of "create"/"onCreate" (creation = `onNewConversation` + "New conversation" icon button;
  also `onSelect`, `onDelete`, no "rename"); ShareDialog.tsx uses `createShareLink`/`listShareLinks`/
  `revokeShareLink`/`handleCopy`; GraphFilterPanel.tsx uses `onToggleNodeType`/`onToggleEdgeFamily` with
  state keys `nodeTypes`/`edgeFamilies` — lowercase "edgeFamily" substring is ABSENT (capital E + plural).
  Grep the actual handler names (or case-insensitive stems like `edgeFamil`), not the doc's verb.
- **`class Origin` lives in `domain/user_content.py`** (`class Origin(StrEnum)` CANONICAL/CANDIDATE/USER),
  NOT domain/change_set.py — a change_set-anchored check false-FAILs; "grep the whole app tree before
  failing" covers enum locations too.
- Absence-check techniques re-confirmed: "no search endpoint" = scan every `@router.<verb>(...)` decorator
  path string in `spoilerless/app/api/*.py` for "search" (empty → PASS); "no tag field" = `\btag\b`
  absent in BOTH `domain/user_content.py` and `repository/user_content.py`; project-spec §13 has zero
  theme/theming/dark-mode text (absence supports the "not classified out of scope" claim) and does list
  mobile/responsive as future breadth.

## project-spec.md re-verify pass (2026-08-16) — 90/92, TWO NEW stale gap-item FAILs
(CLOSED by iteration-2 fix — both gap bullets removed; final subsection: 123/123)

Re-verify after the matched-Claim-gating ×2 + ROADMAP-anchor fixes. All 3 fixes HOLD:
§3.2 L111 + §7 L211 now describe `visible_claim_where()` re-application correctly
(verified against the four query constants' bodies); L28 cites `ROADMAP.md §8 item 6`
= `## 8. Known gaps and unresolved risks`, numbered item 6 "Production operations"
(the old `§8.6` was dead). Baseline: `.planning/tmp/verify-project-spec.md.json`
(fresh tally 92 vs first-pass 56 — per-line granularity; report the honest fresh tally).

**GAP-LIST ITEMS ARE LIVE CLAIMS (new rule, generalizes the known-bug rule):** §13-style
"Current gaps and scope boundaries" lists assert absence ("not implemented") — re-check
EVERY item each pass; code gains features without doc updates. First pass (53/56) missed
these two; both FALSE at HEAD:

1. **L362 "a general CSRF strategy for all state-changing cookie-authenticated routes"
   as a current gap — STALE.** LIVE: `CsrfGuardDependency = Annotated[None,
   Depends(verify_origin)]` (api/deps.py) is wired into ALL 26 state-changing routes
   (candidates ingest/approve/reject/edit, change_set propose/confirm/reject/revert,
   chat sessions/messages/stream, progress POST, settings PUT llm, share create/revoke,
   revisions revert, every user_content write). Only GETs are guard-free. Decisive
   check: split the router file on `\n(?=@router\.)` and confirm every POST/PUT/PATCH/
   DELETE block contains the guard (26/26).
2. **L360 "multi-user authorization/ownership across currently unauthenticated
   user-content, revision, and candidate routes" — STALE.** LIVE per-route deps
   (alias-aware scan): user_content writes = CurrentUserDependency + ownership WHERE
   (`$is_admin = true OR note.user_id = $user_id`); revisions revert =
   CurrentUserDependency; candidates ingest = CurrentUserDependency, approve/reject/edit
   = RequireAdminDependency. Only candidate list/detail GETs are user-less
   (boundary-validated reads).

Reusable facts re-verified this pass (reuse, don't re-derive):
- `visible_claim_where()` body (spoiler/filter.py): `visible_from_order IS NOT NULL AND
  <= $visible_until_order AND origin IN ['canonical','candidate'] AND claim_type <>
  'user_authored' AND (valid_from_order IS NULL OR <= $visible_until_order) AND
  (valid_until_order IS NULL OR >= $visible_until_order)` — matches the doc's "its
  visible_from_order, origin allowlist, claim_type, and validity window" VERBATIM.
- All four retrieval lookups (retrieval/tools.py) = `MATCH (claim)-[rel:SUPPORTED_BY |
  REFERS_TO]->(node) WHERE claim.id IN $claim_ids AND <visible_claim_where()> AND
  rel.visible_from_order ... AND node.visible_from_order ...` — relationship AND node
  gated, matched Claim re-gated.
- **Ontology YAMLs are ground truth for project-spec §4, not the app runtime:**
  node_types.yaml structural = [Series, Season, Episode, Scene] — Season/Scene ARE in
  the committed ontology v0.1 even though absent from `spoilerless/app/` (the
  ARCHITECTURE.md "no Season/Scene" fix does NOT apply to the YAML claim). Never fail
  project-spec §4 Season/Scene on the app-runtime fact. relation_types.yaml = exactly
  27 (4/6/10/4/3); claim_types.yaml = 5 types / 5 statuses / 4 confidence.
- CandidateRepository class + `list_candidate_claims` live in **graph/candidates.py**
  (repository/candidates.py does NOT exist); list query = `WHERE claim.origin =
  'candidate'` + conditional `AND claim.visible_from_order <= $visible_until_order`.
  `_require_resolved_boundary` in api/candidates.py = 1 def + 2 call sites (list +
  detail); 422 INVALID_REQUEST on omitted boundary.
- GraphResponse lives in **domain/graph.py** (not domain/visualization.py);
  `enforce_graph_closure` model_validator there (dangling-edge ValueError).
  VisualizationView(6)/ExpansionKey(7) Literals are defined in **api/graph.py**, not
  domain/.
- ci.yml: `on: [pull_request]`; backend job = neo4j service (image
  neo4j:2026.06.0-community) + `uv run --project spoilerless python -m
  spoilerless.app.graph.setup` + `uv run pytest` + DB-pollution gate (PROB-22, step
  "Assert no scratch/candidate residue after suite"); frontend job = npm ci / npm run
  build / npm run lint / npm audit --audit-level=high. release.yml first comment is
  literally "Staged-promotion skeleton (carry-over 09-07)".
- Frontend: settings component is `SettingsPage` (no SettingsPanel); the ONLY
  `<a href>`/`<Link to>` anchors in frontend/src are ShareView.tsx home links —
  DetailPanel renders `Source: {sourceLabel} - {evidence.locator}` as plain text, so
  "no navigable source links" PASSes.
- Alias-aware per-route dep one-liner (caught everything this pass):
  `re.split(r'\n(?=@router\.)', text)` then per block
  `re.findall(r':\s*([A-Za-z_]+(?:UserDependency|AdminDependency|Dependency))|Depends\((\w+)\)', block)`.

### project-spec.md iteration-2 re-verify (2026-08-14+) — 123/123, stale-gap bullets REMOVED

CLOSES the 90/92 section above: the two stale §13 gap bullets (L360 multi-user
authorization, L362 general CSRF strategy) were REMOVED from the doc by the fix —
authz/CSRF are implemented (routes gated + `CsrfGuardDependency` wired into every
state-changing route), so listing them as current gaps was false. Full fresh
re-verify = **123/123, `failures: []`**; baseline
`.planning/tmp/verify-project-spec.md.json` OVERWRITTEN (90/92 → 123/123).
§3.2/§7 gating phrasing + `ROADMAP §8 item 6` citation still correct — do not
re-fail. Fresh tally 123 vs baseline 92 = per-line granularity (ARCHITECTURE
276→533 precedent); report the honest fresh tally.

New traps from this pass (generalize to any doc verify):
- **Concatenated query constants — the gating fragment is a function CALL**: the
  four retrieval lookups are built as `NAME = (\n """\\\nMATCH ... """ +
  visible_claim_where() + """ ..."""`. A one-string-literal block scan finds NO
  `visible_claim_where` text inside any single literal — scan ~1200 chars after
  `NAME =` for `visible_claim_where()` WITH parens (+ `SUPPORTED_BY`/`REFERS_TO`).
  The def lives in spoiler/filter.py and is imported into tools.py — don't fail a
  gating claim because the def isn't in the caller's file.
- **StrEnum values vs Literal extraction**: `RevisionAction(StrEnum)` has UPPER
  member names with string values (`CREATED = "Created"`) — extract `= "..."`
  lines; a `Literal[...]` capture pulls in following comment/field text.
- **Repository-layer logging**: "hard deletion keeps the revision record" is proven
  in `repository/user_content.py` (`RevisionAction.DELETED`, 9 `log_revision`
  calls) — api/user_content.py + services/user_content.py have ZERO revision hits;
  grep the repository layer before failing a revision-logging claim.
- **Absence-grep benign-hit list (spoilerless/app)**: `opensubtitles.org` appears
  ONLY as source-locator strings in seed/example data (not ingestion);
  `automatic` only in comments ("automatic rollback-on-exception", "never automatic
  graph communities"); `vector` only in "leak vector" comment; "event source" only
  in "no editorial event source is wired yet" comment. Context-check every absence
  hit before failing.
- **test_retrieval_tools.py live count is 40 tests, NOT 4** (the 08-03-era fact
  bank in the spoiler-threat-model section is stale on the count — the file grew).
  It is also the cheapest DB-free verification evidence for retrieval-gating
  claims: `unset PYTHONPATH && uv run pytest spoilerless/tests/test_retrieval_tools.py -q`
  → 40 passed, no Neo4j needed (beats the full suite, which needs live local Neo4j).
- **Multiline-signature defs**: `def _require_resolved_boundary(\n ... \n) -> None:`
  defeats `def NAME\([^)]*\):` regexes — slice from `find("def NAME")` +1100 chars
  and check `422`/`INVALID_REQUEST` there (`http_error(422, "INVALID_REQUEST", ...)`).

### phase-10-golden-path.md iteration-2 re-verify (2026-08-14+) — 28/28, 34→32 count fix HOLDS

Re-verify after the surgical fix (L11 "App.test.tsx four-tab suite (34 tests)" → 32).
**28/28, `failures: []`** (`.planning/tmp/verify-phase-10-golden-path.md.json` overwritten).
Live App.test.tsx = **32** `it(` (28 at 316b938, 31 at b133ee7 — "34" was never true in
history; the 32nd came with the 260814-viz wiring). For UAT rows re-verified AFTER the
doc date, a count parenthetical matching LIVE HEAD passes; the earlier FAIL existed only
because 34 matched nothing. The historical "392-test full frontend suite" re-produced
EXACTLY (42 test files, 392 `it(` via `git ls-tree` + per-file `git show` at 316b938 —
zero tolerance at the pinned commit; the ±4 tolerance note applies to live-suite
comparisons, not pinned-commit counts).

New traps (generalize to any UAT/checklist re-verify):
- **Route-path substring trap (doc-side)**: doc says wired to `/graph/expand` —
  `'"/expand"' in graph.py` returns False; the live decorator is
  `@router.get("/{series_id}/graph/expand")` (APIRouter prefix `/api/series`). Verify
  route claims with the full path-with-placeholder string, never the bare suffix.
- **Quick-task test counts: the quick-task SUMMARY.md is decisive, not raw greps**:
  "4 resize tests" — App.test.tsx has SIX `resize` occurrences (other tests); the
  authoritative count is `260813-wyp-SUMMARY.md`'s ref list (render/aria, keyboard, drag,
  clamps = exactly 4, "appended inside the four-tab describe").
- **UI-rule token absent from code ≠ FAIL — check the BEHAVIOR**: "one-primary-region"
  exists NOWHERE in the repo except the doc itself, yet the row PASSES: UAT rows are
  historical records + the behavior IS tested (App.test.tsx ~L795 "graph workspace is the
  primary region and no timeline rail is mounted" test) + `max-sm` breakpoints in
  App.tsx/DetailPanel.tsx/ChatSheet.tsx. Never fail a backstop row on a missing
  design-rule token when the behavior it names is exercised by a live test.
- **Backstop test claims can live outside the named suite**: UI-TEXT-01 "long-text copy
  tests" are in ChangeSetCard.test.tsx ("wraps (never truncates) ... very long entity
  label") + MessageBubble.test.tsx ("wraps a very long assistant message..."), NOT
  DetailPanel.test.tsx. Grep repo-wide for the behavior keywords before failing.
- **Chunk-name string in prose ≠ chunk exists**: 'chat-llm' appears in
  run_backend_tests.py BOTH in the CHUNKS dict AND in a wall-time comment
  ("chat-llm ≈ 7 min") — confirm the name INSIDE the dict block
  (`CHUNKS: dict[str, list[str]] = {`; match `CHUNKS\s*[:=]` or the annotated form).
  run_phase10_backend_tests.py (CHUNK_RUNNER only) re-confirmed as the wrong file.
- **Root "helpers" are single-doc hard-coded scripts**: `verify_all_claims.py`
  (ARCHITECTURE.md) and `.planning/tmp/run_verify.py` (DEPLOYMENT.md) are NOT generic
  verify-*.json validators — don't run them to validate another doc's artifact.
- **Fresh verification evidence for the artifact itself**: a `python -c` strict contract
  check of the written JSON (key set, doc_path verbatim, passed+failed==checked,
  len(failures)==claims_failed, failure shape) with asserts + exit 0 IS the verification
  for the changed path; repo pytest/vitest suites are inapplicable to a read-only doc
  artifact (verifier role is filesystem-only — say so, never fabricate test output).

## backend-modules.md re-verify pass (2026-08-16) — 578/580, TWO NEW BLOCKERs beyond the 8 fixes

`docs/reference/backend-modules.md` re-verified after "8 surgical fixes" (candidates.py
repository claims L50/L98, model_records L113, ShareTokenCreate→ShareCreateRequest L121,
get_driver→get_database L173, get_neighborhood-distance L212, _propose_changeset→
_propose_changeset_executor L227, SYSTEM_PROMPT_VERSION L232). ALL 8 HOLD — but the fresh
full pass found **2 NEW BLOCKERs the first pass (427/419+8) missed**:

1. **L220 `_TOOL_INPUT_MODELS` and 2. L221 `_TOOL_EXECUTORS` do not exist** — the single
   tool registry `TOOL_SPECS: list[ToolSpec]` (PROB-09/#63) REPLACED the three parallel
   tables. TRAP: both identifiers still appear in pipeline.py:425's comment ("replaces the
   three parallel tables (TOOL_SCHEMAS / _TOOL_EXECUTORS / _TOOL_INPUT_MODELS)") — a bare
   occurrence grep PASSES a false claim. **Comment-only occurrence ≠ existence: check for a
   DEFINITION (`NAME\s*[:=]`), never mere occurrence.** Per-spec fields:
   input_model/executor/result_bucket/requires_user/requires_chat_session; TOOL_SCHEMAS is
   DERIVED from TOOL_SPECS; `_TOOL_SPECS_BY_NAME` dict; CONTEXT_SECTIONS defined in
   retrieval/context.py:16 (`tuple[str, ...]` annotation).

Reusable live facts (re-derived this pass — reuse, don't re-derive):
- Router prefixes carry `{series_id}` THEMSELVES: progress.py prefix
  `/api/series/{series_id}` + decorator `"/progress"`; chat.py
  `/api/series/{series_id}/chat`; change_set.py `/api/series/{series_id}/change-sets`;
  candidates.py `/api/series/{series_id}/candidates`; user_content.py `/api/series` +
  `"/{series_id}/notes"`/`"/custom-nodes"`/`"/custom-relationships"`; revisions.py
  `/api/series`. Full path strings NEVER appear — verify prefix + bare decorator path.
- Rate limiter instances are NAMED: `login_rate_limiter` (api/auth.py),
  `chat_send_rate_limiter` (api/chat.py), `content_write_rate_limiter`
  (api/user_content.py ×9) — the bare name `RateLimiter` appears in NO route module;
  grep the instance names from services/rate_limit.py.
- `LLMProviderDependency = Annotated[LLMProvider, Depends(get_llm_provider)]` is defined
  in **services/chat.py:437**, NOT api/deps.py.
- Session tokens: `core/tokens.py` (PROB-09/#68) owns `generate_token(nbytes=48)` =
  secrets.token_urlsafe + `hash_token` = sha256; repository/session.py imports them —
  grep core/tokens.py, never repository/session.py, for token_urlsafe/sha256.
- deps.py: `DatabaseDependency = Annotated[Neo4jDatabase, Depends(get_database)]` —
  **Depends() takes the function OBJECT, so `get_database\(` never matches**; grep
  `Depends\(get_database\)`. `get_database()` body (graph/database.py:135) returns
  `request.app.state.neo4j`. AuthService built kwargs-style
  (`AuthService(user_repo=UserRepository(database), session_repo=..., verifier=ProductionGoogleVerifier())`);
  admin gate is `if user.get("role") != "admin"` (deps.py:112).
- Config AURA/NEO4J aliases: `validation_alias=AliasChoices("aura_uri", "neo4j_uri")` —
  lowercase field names; the literal `AURA_` appears NOWHERE in config.py (pydantic-settings
  maps env AURA_URI→aura_uri case-insensitively).
- fetch_graph seven queries: count `execute_query\(` INSIDE the `def fetch_graph` body
  slice = 7 (file-wide = 9: +get_series_meta +resolve_boundary's BOUNDARY_QUERY). Constants
  are IMPORTED from spoiler/filter.py (SERIES_QUERY..EVIDENCE_QUERY + BOUNDARY_QUERY +
  VISIBLE_USER_RELATIONSHIPS_QUERY), not defined in services/graph.py.
- Candidate review: `_approve_claim_work(tx, command: dict[str, Any])` etc. — mutable dict
  commands into execute_write (graph/candidates.py:179-239).
- Cache fail-open evidence: graph_cache.py `if not get_settings().redis_url: return None`
  + try/except Exception → None; redis_client.py itself has NO try/except (callers guard).
- Logging middleware: safe_headers allowlist (user-agent/content-type/accept) + docstring
  "Never logs ... X-LLM-* / Cookie / Set-Cookie / Authorization ... body" — a regex
  `log.*X-LLM` matches the docstring's NEGATION sentence → false FAIL. Adjudicate from the
  allowlist + docstring, not a log-line grep.
- user_content.py cache invalidation: split on `\n(?=@router\.)`; notes write blocks have
  NO invalidate_series; ALL 6 custom-node/rel write blocks DO; read routes never do.
- LLMEvent (llm/provider.py) fields: kind/text/tool_name/arguments/content/citations/
  graph_focus/proposed_change_set — NO credential field. Slice the class body between
  `class LLMEvent(` and the first `@classmethod` before grepping (file-wide `.*key` hits
  unrelated docstrings).
- OpenAICompatibleProvider's vllm/ollama serving lives in services/chat.py:168
  (`if provider not in ("openai_compatible", "vllm", "ollama")`) — provider.py never names
  vllm/ollama; `LLM_PROVIDERS` tuple is in domain/settings.py.
- test_retrieval_pipeline.py `_StubDatabase` routes canned rows by distinctive Cypher
  fragment (`if fragment in query`) — that IS the "content-marker stub" mechanism; 16
  tests, DB-free (fast pytest evidence for pipeline claims).
- lifespan: `try: await database.verify_connection() except Exception: pass` → `else:
  create_task(_session_sweep_loop())` (sweep ONLY after successful check); finally closes;
  SESSION_SWEEP_INTERVAL_SECONDS = 3600.
- backend-modules.md has ZERO `VERIFY:` markers (count 0 — don't expect any).

New batch-harness traps (generalize to ANY doc verify):
- **Python 3.11 f-string backslash SyntaxError**: `f"...({cnt('f', r'...\s+...')})"` is a
  SyntaxError (backslash inside the {expression}). Precompute:
  `(lambda n: (ok() if n >= X else (False, f"..({n})")))(cnt(...))`. Hit 3× this pass.
- **Typed-assignment regex**: `TOOL_SCHEMAS: list[dict[str, Any]] = [`,
  `ERROR_CODES: frozenset[str] = frozenset({`, `DEFAULT_FALLBACKS: dict[str, str] = {`,
  `CONTEXT_SECTIONS: tuple[str, ...] = (` — all defeat `NAME\s*=`. Match `NAME\s*:` or
  `NAME(?::[^=]*)?\s*=\s*`.
- **Override-block call order**: an "adjudication overrides" block appended to an existing
  script must run AFTER the check loop populates results — called before, it silently
  replaces nothing (41 failures stayed 41). Also: override keys must be SUBSTRINGS of the
  actual claim text (`"route /{series_id}/chat"` ≠ claim `"router prefix /api/series +
  /{series_id}/chat route"`) — 4 of 6 override misses this pass were substring mismatches.
- **`cnt()` helper takes a FILE path**: passing a sliced function-body string to cnt()
  raises FileNotFoundError (it rd()s its arg); count on the string with
  `len(re.findall(pat, body))` instead.
- **Route-family "uses X" claims**: route modules consume deps by ALIAS
  (AuthServiceDependency, ShareRepoDependency, LLMProviderDependency) — the bare class
  name (AuthService, ShareRepository) never appears; PASS by flow adjudication
  (alias → deps.py construction), same family as the type-alias dep trap.
- **Re-verify MUST be a fresh full pass**: the first pass's 8-failure list was complete for
  ITS granularity but missed the two registry identifiers; a re-verify that only re-checks
  the named fixes would have reported 580/580. New blockers surface on fresh extraction.

### backend-modules.md FINAL re-verify (iteration 2, 2026-08-16+) — 659/659, failures []

Closes the 578/580 section: iteration-2 fix (L220 `_TOOL_INPUT_MODELS` + L221
`_TOOL_EXECUTORS` → `TOOL_SPECS` per-spec `input_model`/`executor`) HOLDS; fresh full pass
= **659/659, failures: []**, artifact overwritten. Tally: 504 automated + 13 bare routes
+ 8 deps + 134 behavior checks — differs from 580 by method; compare PASS/FAIL state.
New pins (reuse, re-verify each pass):
- `_propose_changeset_executor` pipeline.py:367, `executor=` at :529;
  `awaiting_confirmation` domain/change_set.py:272 + graph/change_set.py:53.
- Share TTL `ttl_seconds: int = 2592000` at repository/share.py:28/72/149 (protocol,
  in-memory, Neo4j); api/share.py has ZERO ttl occurrences ("omits ttl_seconds" ✓).
- `user_safe_node_types` (graph/ontology.py) == CustomNodeType StrEnum values
  (domain/user_content.py) — "ontology-validated labels" = enum↔property equality.
- FastAPI literal is MULTI-LINE (main.py:164-167) — single-line literal checks false-FAIL;
  `include_router(` in main.py = exactly 11 ("eleven routers" ✓).
- Sweep ordering: `verify_connection()` main.py:146; sweep `create_task` ONLY at :152
  (comment :149) — "sweep only after successful connection check" ✓.
Module-map doc traps (any backend-modules-style doc):
- Bare filenames in tables resolve by SECTION package (api/, domain/, graph/, spoiler/,
  llm/, cache/, repository/); multi-segment paths vs spoilerless/app or repo root;
  `pyproject.toml` at repo root (NO package.json here). One-form-only resolvers
  false-FAIL dozens of claims (42 in one pass).
- ABSENCE claims ("no `repository/candidates.py`") PASS when the file is absent —
  special-case them or the extractor reports them as failures.
- Multi-line route decorators (`@router.post(\n "/google",` auth.py:93; settings.py:34/47)
  and multi-line FastAPI literals break single-line regexes — inspect the file first.

### spoiler-threat-model.md FINAL re-verify (2026-08-16+) — 157/157, failures []

Full fresh pass after the 32-fix iteration-2 (artifact overwritten:
`.planning/tmp/verify-spoiler-threat-model.md.json`; fresh tally 157 vs baseline 142 —
honest fresh extraction, per-line granularity precedent). ALL 32 fixes HOLD; zero stale
pins remain. Nine script-flagged items each adjudicated PASS — every one is a reusable
adjudication rule:

- **Pin may target the ANNOTATION line, not the def line**: `reject_change_set` def is
  at api/change_set.py:131, but the doc's `:134` is EXACTLY `user: CurrentUserDependency,`.
  The doc pins the dependency it claims, not the def. Before failing a "takes only X
  dependency" pin, check the signature's annotation lines — a def-line-only check
  false-FAILs.
- **Pin-SET claims are sets, not ordered tuples**: doc "server ceilings at
  retrieval/tools.py:27,30,31,32" — live: 27 = MAX_TRAVERSAL_DEPTH, 30 = MAX_PATH_HOPS,
  31 = MAX_SEARCH_RESULTS, 32 = MAX_RESULT_LIMIT (values all correct). The doc never maps
  constant→line; verify the SET of lines, never an assumed order.
- **Dataclass-instance registries defeat dict-key regexes**: `TOOL_SPECS: list[ToolSpec]
  = [ToolSpec(name="search_entities", ...)]` — `"name": {` / key regexes return junk keys
  ('description','function','type'). Extract `name="..."` kwargs from the block. Live =
  exactly the doc's 12 tools (11 reads + propose_changeset; fetch_episode_codes absent).
- **Boundary-attribution nuance (reuse for ANY graph-route doc)**: `get_graph` resolves
  the boundary INLINE (api/graph.py:119-140: `requested = 1 if user is None ...`,
  `min(visible_until_order, record.view_as_of_order)` + `effective_view_order`) while
  `_resolve_effective_boundary` (:397) serves path/export. A doc saying all three routes
  resolve "in _resolve_effective_boundary" PASSES: the inline comment (119-123)
  reproduces the claim verbatim (anonymous fixed at 1; persisted-episode check vs the
  effective order). Body-scan for the inline equivalent before failing
  helper-attribution claims — same family as the alias-dep blind spot.
- **Class-def pins**: "GraphNode.visible_from_order: int = Field(ge=1) (domain/graph.py:11)"
  — class at 11, field at :15. Pin names the class that carries the field; content AT the
  pin is the right symbol → PASS (same rule as PROBLEMS.md banner pins: flag only when
  content at the pin is false).
- **Range-pin formatting off-by-one**: ChangeSetStale→409 entry spans api/exceptions.py
  61-67 (`(` 61, ChangeSetStale 62, 409 63, "CHANGESET_STALE" 64); doc cites 62-67 → PASS
  (the mapping content IS at 62-67; the paren is formatting). `_SENTINEL_SPECS` itself:
  assignment at :44, entries through :69 — cite the entry range, not the assignment line.
- **Projection-line pins**: services/graph.py:92 = `projected_edges = [` — the doc's
  "edges projected from visible claims" pins the assignment line; don't require the word
  "claim" ON that line (the GraphEdge construction below it uses
  claim.subject_id/object_id/predicate).
- **EpisodeSelector.tsx exact pins confirmed**: :25 isLocked helper, :61 Lock icon
  render, :62 `{episode.display_title ?? episode.title}`, :85
  `{episode.code} — {episode.display_title ?? episode.title}` — all four landed.
- **Supporting pytest evidence for doc artifacts (DB-free batch, ~55s)**:
  `unset PYTHONPATH && uv run python -m pytest spoilerless/tests/test_rate_limit.py
  test_frontend_contract_doc.py test_citations.py test_retrieval_tools.py -q` →
  59 passed (8+3+8+40). Use this batch when the harness demands pytest evidence on a
  doc-verify artifact (JSON contract re-parse remains the artifact's own verification;
  never fabricate output).
