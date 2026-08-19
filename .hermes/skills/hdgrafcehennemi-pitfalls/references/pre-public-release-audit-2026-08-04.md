# Pre-public-release audit — method & evidence inventory (2026-08-04)

Ledger: `docs/PROBLEMS.md` (41 numbered problems). This file records HOW the
audit was run and the raw evidence, so a future session can re-verify, extend,
or track fixes without re-deriving. Read `docs/PROBLEMS.md` first — it is the
canonical problem list.

## Method (read-only, no code changes)

1. **Map the surface**: `find backend/app -name '*.py'`, route-decorator grep
   (`grep -rn "@router\.\(get\|post\|put\|patch\|delete\)" backend/app/api/*.py`),
   then per-router auth-dependency grep (`CurrentUserDependency` /
   `OptionalUserDependency` / `require_current_user`).
2. **Ground truth from the LIVE server** (user's uvicorn was already running on
   :8000 — verify with `curl /health` before spawning your own):
   `curl -s localhost:8000/openapi.json` → count paths/ops, enumerate the
   no-auth path list. This beats reading docs: API.md claimed 44 ops/32 paths,
   live = 45 ops/33 paths.
3. **Run the suites for current numbers**: targeted pytest
   (`pytest backend/tests/test_seed_idempotency.py test_openapi_contract.py -q`
   → 3 failed/14 passed, the documented red baseline), full vitest
   (`NODE_ENV=test CI=1 npx vitest run` → 185/1; the 1 failure PASSES in
   isolation → flaky/order-dependent), `npm run lint` (28 errors at HEAD),
   `npx tsc -b` (clean).
4. **Walk the risky modules** (auth, settings, user_content, candidates,
   revisions, chat, policy, database, seed) reading full files — the highest-
   value bugs were found by READING, not by tests.
5. **Docs drift check**: grep counts/claims in docs vs openapi + source
   (ARCHITECTURE.md claimed `proposed_change_set: null` and ungated counts —
   both stale; API.md route counts off by the dev-login route).
6. **Confidentiality scan** (see the `public-release-audit` skill for the
   general recipe): full-history secret grep, `git ls-files` env check,
   `git check-ignore -v` verdicts, untracked-dir audit, git-author emails,
   local-path grep.

## Verified evidence highlights (2026-08-04)

- **Anonymous write surface**: 19 of 33 paths need no session; 14 WRITE ops
  across 11 templates — user_content (notes/nodes/relationships CRUD),
  candidates (ingest/approve/reject/edit), revisions revert. `useAuth` only in
  `App.tsx` + `LoginPage.tsx`.
- **LLM-key exfil**: `domain/settings.py:26-29` docstring admits any
  authenticated user can redirect the shared provider to an attacker host;
  provider sends stored key as `Authorization: Bearer` / `x-goog-api-key` to
  the configured `base_url`. SettingsPage exposes the `base_url` input.
- **New bugs read from source** (see runbook SKILL.md section for one-liners):
  session-id second-resolution collision; fabricated candidate `revision_id`;
  orphaned chat user-messages on failed turns + silent SSE `except Exception`;
  `validate_visibility_order(None)` → TypeError → 500; docker-compose
  publishes Neo4j 7474/7687 with `neo4j/hdgraf-local-password`; app = `neo4j`
  admin superuser; no security headers; error handlers never log originals.
- **Suites at HEAD**: backend 3 red (`test_seed_idempotency` ×3,
  `{'relationships': 33} != {'relationships': 27}` — live-DB drift), FE 1 flaky
  (App.test.tsx e2e), lint 28 errors, tsc clean, build warns >500kB chunk.
- **Docs drift**: API.md 44/32 vs live 45/33; ARCHITECTURE.md §562
  `proposed_change_set: null` false since 07-07; §596 progress/episode
  validation false since 07-02, counts-endpoint gating false since 07-05.

## Confidentiality scan results

- ZERO credentials in tree or full history (only placeholders + prose warning
  against `GOOGLE_CLIENT_SECRET`; one `NEO4J_PASSWORD=your-password` in an old
  docs commit).
- Real secrets only in gitignored files: `.env` (GOOGLE_CLIENT_ID +
  AUTH_DEV_CODE), `backend/.env`, `frontend/.env.local` (`*.local` rule).
- Personal Gmail `oyunlarinefendiler@gmail.com` in git AUTHOR history (older
  commits; newer use the GitHub noreply address). Permanent once public —
  `git filter-repo` if the user cares.
- Untracked NON-gitignored leak dirs: `docs/internship-report/` (user's
  internship report — sensitive), `.hermes/`, `.claude/`. `git add -A` stages
  all three. Add to `.gitignore` before any public push.
- Tracked `.planning/` files leak `C:\Users\arhan\...` local paths
  (`03-03-SUMMARY.md`, `07-08-ACCEPTANCE.md`, `PITFALLS.md`).
- GitHub API returns `Not Found` for the remote (`vinnipukh/hdgrafcehennemi`)
  — private or removed; the 47 unpushed commits have no confirmed backup.
- Seed data: hotlinked `static.wikia.nocookie.net` images (copyright exposure),
  episode titles + 9 one-line plot-summary evidence fragments (low risk).

## Moving-target warning

The working tree changed MID-AUDIT: an uncommitted auth refactor (dev-login
removal + `allowed_emails` allowlist / `AUTH_EMAIL_NOT_ALLOWED`) appeared in
api/auth.py, core/config.py, domain/auth.py, services/auth.py, test_auth.py,
contract tests, frontend-api-contract.md, useChatMessages.ts. Another agent
(Claude Code in `.claude/worktrees`) or the user edits concurrently. ALWAYS
re-run `git status` + `git diff` before trusting line-number evidence, and
state which commit/working-tree state an audit covers.
