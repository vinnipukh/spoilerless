# Docs layout & conventions (2026-08-12 restructure)

User-driven restructure (commit `5cb6451`): docs grouped by **lifecycle**, not
date/version. Rule the user stated explicitly: **thematic names, never
`backend_refactor_03.md`-style throwaway/versioned filenames.**

## Current layout (old → new)

Canonical GSD docs keep uppercase names + fixed paths (never move them —
gsd-docs-update `resolve_modes` rule). Everything else moved:

| Old | New |
|---|---|
| `docs/API.md`, `ARCHITECTURE.md`, `CONFIGURATION.md`, `GETTING-STARTED.md`, `DEVELOPMENT.md`, `TESTING.md`, `DEPLOYMENT.md`, `PROBLEMS.md`, `ROADMAP.md` | unchanged (canonical / ledger / backlog stay at docs root) |
| `docs/PROJECT-SPEC.md` | `docs/architecture/project-spec.md` |
| `docs/SPOILER-{DEFERRED-DESIGN,TERMINOLOGY,THREAT-MODEL}.md` | `docs/architecture/spoiler-{deferred-design,terminology,threat-model}.md` |
| `docs/frontend-api-contract.md` | `docs/reference/frontend-api-contract.md` |
| `docs/BACKEND-MODULES.md` | `docs/reference/backend-modules.md` (snapshot marker added) |
| `docs/FRONTEND-COMPONENTS.md` | `docs/reference/frontend-components.md` (snapshot marker added) |
| `docs/RUNBOOK.md` | `docs/ops/runbook.md` |
| `docs/BACKEND_DEPLOY_FIX.md` | **folded into** `docs/ops/runbook.md` appendix, file deleted |
| `docs/FEATURE-IDEAS.md` | `docs/ideas/feature-ideas.md` |
| `docs/FEATURE-RESEARCH.md` | `docs/ideas/feature-research.md` |
| (new) | `docs/README.md` — index + stability-class table |

## Stability classes (docs/README.md — the anti-drift convention)

- **Generated / test-locked**: `reference/frontend-api-contract.md`, `API.md`
  — never hand-edit counts; `test_frontend_contract_doc.py` +
  `test_openapi_contract.py` lock them. Regenerate from `app.openapi()`.
- **Decision records**: `architecture/*`, `ARCHITECTURE.md` — written once,
  changed only when the decision changes; per-change noise → `PROBLEMS.md`.
- **Snapshots**: `reference/backend-modules.md`, `frontend-components.md` —
  dated, "verify against live tree before trusting".
- **Living process**: `ops/runbook.md`, `DEPLOYMENT.md`, `PROBLEMS.md`,
  `ROADMAP.md` — appended to, existing sections not rewritten per commit.
- **Ideas**: `ideas/*` — no status until scoped against project-spec
  invariants.

## Code paths that reference doc paths (update together)

- `spoilerless/tests/test_frontend_contract_doc.py` — `DOC_PATH` =
  `docs/reference/frontend-api-contract.md` (this test breaks if the doc
  moves; it locks the 50-op inventory).
- `spoilerless/app/spoiler/policy.py` + `spoilerless/tests/test_spoiler_policy.py`
  docstrings mention `docs/architecture/spoiler-terminology.md`.
- `scripts/run_backend_tests.py`, `scripts/sweep_error_codes_09_05.sh`
  (DOC_FILES list), untracked verify helpers `run_doc_verification.py` /
  `run_verification.py` / `verify_all_claims.py` (claim checks incl.
  `check_file_path(306, ...)`).

## Doc-restructure recipe (reusable)

1. **Inventory**: `grep -rln "<moving-file>" --include="*.md" .` for referrers;
   then `grep -rno "]\([^)]*<file>"` for exact link forms (same-dir vs
   `docs/`-prefixed vs anchor-suffixed).
2. **Move**: `git mv` tracked files; **plain `mv` for untracked ones**
   (`git mv` hard-fails: "not under version control").
3. **Bulk-fix links**: python exact-substring replace per file — never sed.
   Remember moved files' own links to docs-root need `../`, and paths that
   point at repo root (e.g. `ontology/*.yaml`) need `../../` from
   `docs/architecture/`.
4. **Dangling-link check** (python, resolve every relative md link):
   `re.compile(r'\]\(([^)#]+)(?:#[^)]*)?\)')`, skip http/#, normpath against
   the file's dir, flag non-existent. Target: 0 dangling.
5. **Code/script path constants** — grep the whole repo for the old paths
   (`--include=*.py --include=*.sh`), fix every hit; `.planning/codebase/*`
   knowledge files too. Historical `.planning/phases/*` plans + internship
   report are frozen records — leave them.
6. **Verify**: affected pytest files + doc-claim scripts + full suite.

## Windows / gsd-tools quirks (this host)

- Repo has NO `gsd-core/` — the shim lives at
  `C:/Users/arhan/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs`. Invoke
  with a **Windows-style path**: `node "C:/Users/.../gsd-tools.cjs" query
  docs-init`. `$HOME`-expanded MSYS paths get mangled to `C:\c\Users\...`
  and node throws MODULE_NOT_FOUND.
- `gsd-tools query docs-init` detector is **unreliable on this repo**:
  reported `has_api_routes:false`, `has_tests:false`, `has_package_json:false`
  (wrong — FastAPI routers + 591 tests + frontend package.json exist).
  Correct the classification manually (SaaS + open source → API, DEPLOYMENT,
  CONTRIBUTING queued).
- Terminal heredoc guard misfires on `&` inside content — append file content
  via a short `python -c` instead of `cat >> <<EOF`.

## FE shared helpers (same session, #81)

- `operationTargetRefs(op)` + `OperationRef` in `frontend/src/types/changeSet.ts`
  — single operation→target-ids switch (App focus highlight + ChangeSetCard
  affected list consume it; App skips `create_relationship` explicitly).
- `CitationChip` props = discriminated union `{label}` | `{citation,...}`
  (lean chip — never fabricate a fake Citation again).
- Node-type single registry: `lib/nodeTypes.ts` holds `NODE_TYPES`,
  `CUSTOM_NODE_TYPE_NAMES`, `CustomNodeType`, `ALLOWED_NODE_TYPES`;
  `types/userContent.ts` re-exports the type (needs BOTH `import type` and
  `export type` — re-export alone does not bind the name locally, TS2304).
