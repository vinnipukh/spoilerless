# 08-14 docs-update run — ledger semantics, verifier false-negatives, fix-loop iteration-2 patterns

Full gsd-docs-update run (2026-08-14): 9 canonical docs updated + 24 review docs
verified, 75 failed claims across 15 docs fixed (52 surgical edits), all
re-verified clean after ≤2 fix iterations. Verified live facts and conventions
to reuse next run.

## Verified facts bank (08-14, all re-checked live)
- API: 52 ops / 39 path templates (test_frontend_contract_doc.py); rate limits
  10/300 login, 20/60 chat, 30/60 content-write (services/rate_limit.py);
  ERROR_CODES=32; share TTL 2592000; MAX_PATH_HOPS=4; expansion limit 12/25;
  `POST /graph/path` = optional-session, ONLY unguarded write-shaped route.
- NODE_LABELS = 12 (Series, Episode, Character, Event, Location, Organization,
  Object, Claim, Source, EvidenceFragment, UserNote, Revision) — **NO
  Season/Scene** (those are ontology YAML/data keys, NOT graph labels; a common
  doc-drift trap). STORY_LABELS = 8. RELATIONSHIP_TYPES in seed.py.
- TOOL_SPECS = 12 tools (11 read incl. get_user_notes + propose_changeset);
  `fetch_episode_codes` is an internal helper, not a tool. `$visible_until_order`
  literal occurrences = 27 (not 39).
- Rate limiter is FULLY fail-open (PROB-23): RedisBucket.init() +
  try_acquire_async() both wrapped, degrade to no-op. Disabled-provider 503
  error code = `LLM_DISABLED` (NOT LLM_PROVIDER_DISABLED).
- Retrieval-hop gating COMPLETE (08-14): all 8 claim-selecting queries in
  retrieval/tools.py compose visible_claim_where() — gates the matched Claim's
  own visible_from_order + validity window.
- Share-creation clamps to creator's persisted progress (CR-01, fail-closed to
  1): effective_view_order(min(requested, view_as_of_order), watched_through_order).
- reject_change_set is NOT admin-gated (CurrentUserDependency only, api/
  change_set.py:134, "intentionally NOT gated" comment); confirm IS admin-gated.
- characters.json: 32 chars; 6 carry BOTH image_url + image_source_url.
- /health SERVICE_NAME = 'spoilerless-backend' (main.py:38). No monitoring deps,
  no Dockerfile/.dockerignore, no RENDER_API_KEY. ci.yml = backend+frontend jobs
  with DB-pollution gate; release.yml = skeleton (contents: read, echo-only gate).
- render.yaml service name = **spoilerless-api** (renamed from hdgrafcehennemi-api
  in a0aa33a). Dashboard service name may differ — VERIFY markers for dashboard
  claims. `.python-version` = 3.13.
- VERIFY-marker baselines (verifier counts them): DEPLOYMENT.md = 14,
  CONFIGURATION.md = 5, README.md = 4, API.md = 1.

## LEDGER SEMANTICS — PROBLEMS.md (critical for verifiers)
PROBLEMS.md is a numbered-pass LEDGER: entries under dated pass sections and
entries with RESOLVED banners / FIXED records are HISTORICAL AUDIT TRAIL.
First-pass verifier flagged 11 "failures"; only 2 were live claims (a RESOLVED
banner's `.env.example:10` line pin that moved to line 16, and a FIXED record
overclaiming invalidate_series on the revert path). The other 9 (e.g. "no
LICENSE", "no .github", old line counts, old 50/37 snapshots) are correct
history. Verifier instructions MUST include: flag only live claims
(current-pass rows, RESOLVED-banner statements of current state, still-open
items); historical descriptions left in place per the ledger's own convention
PASS. Without this instruction you get ~10 false failures and risk corrupting
the audit trail.

## HISTORICAL-RECORD SEMANTICS — decision logs + archival note pattern
`.planning/phases/` was emptied by `e62e664 chore: archive v1.3 milestone`
(2026-08-14); phase planning files now live under
`.planning/milestones/v1.3-phases/10-polish-finishing-touches/`. A dated
decision log citing those paths gets ONE archival-note edit (after the header
block: artifacts archived with commit X, references below point at files no
longer in the working tree, surviving path given) — do NOT rewrite the 15
references. Also check for phantom filenames in the table (10-10-11-SUMMARY.md
never existed; real files are 10-10- and 10-11- separately).

## Verifier FALSE NEGATIVES on test-name/line-count claims
Threat-model verifier claimed test_retrieval_tools.py had "4 tests" and
test_citations.py "1 test" — live: **40 and 8** (incl. test_get_evidence_
visible_only, test_get_sources_visible_only, test_find_path_*,
test_hidden_claim_evidence_source_citations_are_rejected). The verifier had
read only the file head. Lessons:
- When a verifier flags a test-name/selectors claim, `grep -c "def test_"` the
  test file yourself BEFORE dispatching a fix — don't trust the flag blindly.
- Re-verification prompts must say: verify test-name claims by listing the
  actual test files.

## Fix iteration-2 patterns (first fixes that missed)
- Count fixes must cover ALL occurrences: runbook's "10 chunks" prose was fixed
  but the Backend Tests table + `# all 10 chunks` comment were missed. Instruct
  fix agents: search the whole file for the number/claim, tables and comments
  included.
- Cross-references need the repo-canonical citation form: ROADMAP §8 is a
  numbered list 1-9 with NO §X.Y subsections — canonical is "§8 item 3", not
  "§8.3". Check the target doc's actual structure before suggesting an anchor.
- "Current gap" lists go stale fast: project-spec §13 listed authz + CSRF as
  gaps already closed at HEAD — when a gap bullet fails, check whether the gap
  was CLOSED and remove the bullet rather than rephrasing it.

## Runner + env dance (guarded backend suite)
- Guarded runner REFUSES while shared container is live (T10-LEAK-09): stop it,
  run, restart: `docker stop spoilerless-neo4j` → run → `docker start
  spoilerless-neo4j` (volume-persisted, zero data risk).
- Runner must be invoked with the venv python: `.venv/Scripts/python.exe
  scripts/run_phase10_backend_tests.py` with PYTHONPATH unset — system `python`
  lacks neo4j (ModuleNotFoundError) and hermes-terminal PYTHONPATH shadows.
- Docker Desktop down: launch `C:\Program Files\Docker\Docker\Docker
  Desktop.exe`, poll `docker info` (~10-60s ready), then rerun.
- `hermes verify` on this repo: default detected recipe = bare `pytest` + stale
  `uvicorn main:app` start — bare pytest is not on PATH in the verify subprocess
  AND unguarded pytest is prohibited by T10-LEAK-09. Only `--phase bootstrap`
  (uv sync) is policy-safe. Fixing the recipe via .hermes/environment.json
  requires user approval (silent write was refused) — ask first, or skip.

## Run bookkeeping
- docs-init still reports has_api_routes=false (JS-biased detector) → queue
  docs/API.md manually as codebase-discovered.
- Wave pairing that works (max 2 parallel doc subagents): readme+architecture,
  configuration+getting_started, development+testing, api+deployment,
  contributing.
- `.planning/tmp/docs-work-manifest.json` is TRACKED; update statuses after
  each wave; validate with a python json-assert script after each edit (cheap,
  catches structure drift). commit_docs=true commits only the 9 canonical files.
- Reviewer's post-run obligation: append the next numbered pass (TWENTIETH)
  to docs/PROBLEMS.md.
- search_files MSYS path-mangling (os error 3 on existing paths) recurs
  constantly in subagents — terminal grep fallback is the established workaround.
