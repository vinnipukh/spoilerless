# Codebase Map Doc Refresh (.planning/codebase/) — workflow & repo facts

Refreshing `CONVENTIONS.md`, `TESTING.md`, `CONCERNS.md` (and siblings) in
`.planning/codebase/` against live code. Last full refresh 2026-08-12 @ `1710d57`
(prev 2026-08-02 @ `0b4c83c`). Each file has YAML frontmatter
(`last_mapped`, `last_mapped_commit`) + a footer date — bump ALL of them to the
new HEAD + date when refreshing. Preserve structure/template; never rewrite
wholesale — verify live, then patch in place.

## Workflow (proven 2026-08-12, PROB-09 wave refresh)

1. **Read each doc fully first** (frontmatter, evidence blocks, line refs) before touching anything.
2. **Find the ledger:** PROBLEMS.md lives at `docs/PROBLEMS.md`, NOT repo root. It is organized as numbered passes (ELEVENTH PASS, TWELFTH PASS…) with per-fix commit hashes and the 584/7 baseline policy — it is the source of truth for concern resolution status + commits.
3. **Mechanical path renames** (e.g. `backend/` → `spoilerless/`): use `patch` with `replace_all=true`. Afterward grep for remaining hits — legitimate PROSE contains the old word too (`backend/FastAPI validation errors`, `backend/frontend images`) and must NOT be replaced. Also handle dots-form `backend.app` → `spoilerless.app` separately.
4. **Verify every claim live** before editing:
   - `git log --oneline -S <symbol> -- <file>` to find the commit that introduced/removed a behavior (first hit is often the mass-rename commit `b94ac6f` — read the second hit).
   - `wc -l` for file sizes; `grep -n "@router\.\|RequireAdmin\|CurrentUserDependency"` for auth coverage of routes.
   - Run the actual gates: `npm run lint` (counts change!), `NODE_ENV=test CI=1 npx vitest run` (get real pass counts).
5. **Concern status markers:** for each concern add `**Status:** RESOLVED / PARTIALLY RESOLVED / OPEN (date: commit) — short note` after the Severity line. Relabel Problem/Risk as `(historical)` when resolved but keep the block for the audit trail. Note residuals explicitly (e.g. "no coverage threshold yet"). Keep 6.5-type "not a defect" items OPEN/N-A.
6. **Report in cavecrew-investigator style:** per doc, bullets of `` `path:line` — symbol — short note `` (each note ≤15 words), then totals (files changed, +/− lines, statuses).

## 2-subagent supplement split (user-preferred 2026-08-12)

For "supplement current docs with N subagents" requests, split by focus groups so each agent owns docs with shared concerns:

- **Agent A (tech+arch):** STACK.md, INTEGRATIONS.md, ARCHITECTURE.md, STRUCTURE.md
- **Agent B (quality+concerns):** CONVENTIONS.md, TESTING.md, CONCERNS.md

Each agent's delegation context MUST be self-contained (children know nothing of the session): repo path; rename fact (`backend/`→`spoilerless/`, app at `spoilerless/app/`); last_mapped commit vs current HEAD + full `git log` window inventory; per-doc stale-path counts (e.g. "ARCHITECTURE.md has 77 `backend/` refs"); stale line counts to recount (STACK.md said Python 93/22,793 lines → actual 122/32,332); "supplement, preserve structure, don't rewrite wholesale"; known fixes to mark RESOLVED.

**Pre-flight checks (batch before dispatching):**
1. `ls .planning/codebase/` — confirm 7 docs exist, may already be current
2. `git log -1 --format='%h %ci' -- .planning/codebase/` — map age vs HEAD
3. `git log --oneline <last_mapped_commit>..HEAD | head -30` — change inventory for subagents
4. `grep -c 'backend/' .planning/codebase/*.md` — stale refs per doc
5. `ls -d backend spoilerless frontend` — confirm which package dir actually exists

**Post-flight verification:** `wc -l` all 7 (no truncation); `grep -c 'backend/'` expect 0 OR legit prose only (inspect each hit with `grep -n`); `grep -l 'last_mapped: 2026-08-12'` → all 7 frontmatters bumped.

## Pitfalls

- Parallel agents editing sibling docs: each reports "X.md modified — not mine" for the OTHER agent's set — expected, not a collision; each touches only its own 3-4 files.
- Long compound terminal one-liners (for-loops chained with `&&`) can hit the command-parser blocklist — split into short separate calls (`wc -l`, `grep -c`, `grep -l` individually).
- `grep -c 'backend/'` catches prose too ("backend/FastAPI validation errors", "backend/frontend images") — never declare done on count 0 without line-level check; dots-form `backend.app` → `spoilerless.app` needs its own replace pass.

## Repo facts (verified 2026-08-12)

- **Date-label pitfall:** commit MESSAGES use `09-XX`/`08-11` labels that do NOT match `git log` dates (rename commit `b94ac6f` is labeled "09-01" but git-dated 08-05). Cite dates from docs/PROBLEMS.md pass convention, never from git dates.
- **Test-suite facts (08-12):** 45 `test_*.py` files, ~17.2k lines; FE = 40 files / 333 tests / ~21s; lint = 0 errors / 39 warnings (all `react-hooks/refs`); CI = `.github/workflows/ci.yml` (pinned `neo4j:2026.06.0-community` service + DB-pollution residue gate) + `release.yml`; local-docker baseline 584 passed / 7 failed (3 doc-contract, 2 seed-image, 2 seed_idempotency) via `source scripts/env-local.sh`; chunked runner `scripts/run_backend_tests.py` (10 chunks, serial ~40m, parallel SLOWER on shared AuraDB).
- **conftest.py now hosts shared infra:** `NoopGoogleVerifier` (AuthService requires verifier, no silent fallbacks — PROB-09/#77), autouse `_disable_rate_limiter` (Redis-backed limiter, guarded on `REDIS_URL`), `live_client`/`seed_live_database`, `cleanup_with_fresh_driver`/`module_cleanup_fixture`, `run_query`/`run_async`.
- **Auth/security resolution commits:** auth-gate of mutation routes `0f3c388` (settings admin-only via `RequireAdminDependency`, candidates ingest=CurrentUser + approve/reject/edit=RequireAdmin, revisions revert=CurrentUser); rate limiters `1f8a3e9` (login/chat-send/content-write); session+share sweep in lifespan `1c7d497`; CI `f9df513`; compose pin `9cf1a4b`; PROB-09 wave (08-11): `bacd536` 503-class WITH fix, `3a3ae40` #71 catch-all-422 removal, `3d6dc33` #80 dead code, `201f347` #61 switchSeries, `e0ab05a` #77 AuthService deps, `00fbcb6` #81 sweep.
- **Still-open concerns (08-12):** 1.2 shared-live-DB hazard (mitigated by env-local.sh + CI container), 1.3 no migrations (only `test_setup_schema_check.py`), 2.4 plaintext LLM key at rest, 3.1 whole-graph reads, 3.2 no client close lifecycle, 3.3 process-local concurrency ceiling, 4.1 god modules (sizes 969/827/850/861/856/1001/909), 5.1 no Node engines, 6.2 no production topology, 6.5 future extraction (N-A).
- 2.2 revisions: revert auth'd but `list_revisions`/`get_revision` still client-supplied `visible_until_order` + unauthenticated — mark PARTIALLY RESOLVED, not RESOLVED.
