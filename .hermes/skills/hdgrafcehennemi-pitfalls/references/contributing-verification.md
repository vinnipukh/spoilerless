# CONTRIBUTING.md verification (claim-map + gate status, verified 2026-08-10)

Re-verify CONTRIBUTING.md against live code after doc fixes. Artifact contract
(`.planning/tmp/verify-CONTRIBUTING.json`): `doc_path`, `claims_checked`, `claims_passed`,
`claims_failed`, `failures[]` with {line, claim, expected, actual}; passed+failed==checked,
len(failures)==failed. Every failure entry needs line/claim/expected/actual.

## Run recipe
1. `cd` repo root; **`unset PYTHONPATH`** before any `uv run pytest ...` (leaked PYTHONPATH
   changes results).
2. Run documented gates exactly as written (status as of 2026-08-10):
   - `uv run pytest spoilerless/tests/test_user_content_models.py` → GREEN: 23 passed (DB-free).
   - `uv run pytest spoilerless/tests/test_frontend_contract_doc.py` → RED: 1 failed / 2 passed.
   - `uv run pytest spoilerless/tests/test_openapi_contract.py` → 2 failed / 7 passed (stale by design).
3. Windows host: `search_files`/`read_file` with MSYS `/c/Users/...` paths fail (IO error
   `Sistem belirtilen yolu bulamıyor`); use native `C:\...` paths or terminal `ls`/`grep`.

## 62-claim map (all PASS unless noted)
- Structure: GSD marker `<!-- generated-by: gsd-doc-writer -->` (L1); title (L2); links
  DEVELOPMENT/TESTING/ARCHITECTURE/PROJECT-SPEC exist (L4); no CODE_OF_CONDUCT.md (L8).
- Layout L23–35: spoilerless/app/{api,domain,services,repository,graph,spoiler,retrieval,llm},
  spoilerless/tests, frontend/src/{api,types,components,hooks}, frontend colocated *.test.ts(x),
  data/dexter, ontology — all exist.
- Setup L41–74: .python-version=3.13; Node ^22.22.2/^24.15.0/>=26.0.0 (jsdom lockfile; README +
  DEVELOPMENT.md); CI Node 24; package-lock.json committed; remote vinnipukh/hdgrafcehennemi.git;
  .env.example `VITE_API_BASE_URL=/api`; scripts/env-local.sh `hdgraf-local-password`;
  spoilerless.app.graph.setup; spoilerless.app.main:app; Vite 5173 (default, not overridden).
- Backend rules L80–87: no formatter/linter/type checker (pyproject: pytest + pytest-asyncio only);
  candidate boundary (L83) matches candidates.py; origins canonical/candidate/user in
  spoiler/filter.py; revert logs REVERTED revision (revisions.py:286); invalidate_series in
  app/cache/graph_cache.py; ontology/*.yaml (claim/node/relation_types).
- API changes L97–105: test_frontend_contract_doc.py exists; docs/frontend-api-contract.md exists;
  test_openapi_contract.py asserts 32 templates (line 202) vs live 37 templates / 50 ops; asserts
  DELETE→204 (lines 220-221, 249-250, 302-304) but /api/share/{token} DELETE documents
  401/403/404/503 — so "stale, do not cite as a passing gate" is accurate.
- Quality gates L113–128: gate1 (test_frontend_contract_doc.py) **FAILS** — see failure below;
  gate2 (test_user_content_models.py) passes; both DB-free; conftest.py = import-path +
  scratch-series helpers, no Neo4j redirect/credentials; no xdist in pyproject; CI pollution gate
  enforces no series_scratch*/origin='candidate' residue.
- Frontend L130–140: scripts test=vitest, build="tsc -b && vite build", lint="eslint ."; vitest
  default = watch mode.
- CI L142–149: ci.yml `on: [pull_request]` only (no push/main trigger, no Vitest); backend job =
  uv sync --frozen + graph setup + full pytest vs ephemeral neo4j service + DB-pollution gate;
  frontend job = npm ci + build + lint + npm audit --audit-level=high.
- Process L151–185: no enforced branch policy/PR template; PRs against main (prose).

## Known failure (2026-08-10)
- L114 gate `uv run pytest spoilerless/tests/test_frontend_contract_doc.py` fails:
  `test_document_has_examples_projection_rules_non_goals_and_pending_status` asserts non-goal
  marker `permissions` in docs/frontend-api-contract.md, but the contract doc removed it
  ("Roles **are** implemented: `UserPublic.role` is `admin|user`"). Fix: drop `permissions` from
  the test's non-goal tuple or restore the marker in the contract doc — then CONTRIBUTING.md's
  focused-gate list is truthful again.
