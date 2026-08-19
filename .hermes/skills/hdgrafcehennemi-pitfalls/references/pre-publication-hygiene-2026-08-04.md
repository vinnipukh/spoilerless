# Pre-publication hygiene + mid-session tree discipline (08-04)

## Repo audit artifact

- `docs/PROBLEMS.md` is the standing pre-publication audit artifact — 41 verified problems,
  ranked CRITICAL/HIGH/MEDIUM, each with file:line evidence and a "survival order" of fixes.
  Before claiming anything about deployability, read it and re-verify the top items against
  live source — it will drift like every other doc in this repo (API.md/ARCHITECTURE.md
  already have documented drift).

## Personal-data state (08-04, user-approved)

- `docs/internship-report/` added to `.gitignore` (the internship report is personal; never
  let `git add -A` stage it).
- `.planning/research/PITFALLS.md` "Sources" lines scrubbed of `C:\Users\arhan\...` absolute
  paths — replaced with repo-relative refs (`.planning/codebase/CONCERNS.md`, `ROADMAP.md`).
  Other files still carry local paths: `.planning/.../03-03-SUMMARY.md` (Temp probe path),
  `.planning/phases/07-.../07-08-ACCEPTANCE.md` (repo header line) — user only asked for
  PITFALLS.md; don't widen scope unasked.
- Live root `.env` contains `AUTH_DEV_CODE` + `GOOGLE_CLIENT_ID` (verified key NAMES only;
  never read values). Never copy `.env` to a server — the dev-login backdoor would go live.
- Personal Gmail `oyunlarinefendiler@gmail.com` is the author on ~590 of ~616 commit records
  (96%); user explicitly accepted it ("no problem with 1") — do NOT propose/run history
  rewrites unless asked. Full history secret/PII scan found ZERO credentials ever committed;
  the only pushed personal data was the author email + Windows local paths in `.planning/`.
- Untracked `.hermes/` and `.claude/` are NOT gitignored — flag before any `git add -A`.

## The working tree can change under you mid-session

Observed 08-04: while a docs audit was in flight, an auth refactor (dev-login removal +
`allowed_emails` allowlist, `AUTH_EMAIL_NOT_ALLOWED`) appeared as UNCOMMITTED edits in
`api/auth.py`, `core/config.py`, `domain/auth.py`, `services/auth.py`, `test_auth.py`,
both contract tests, `docs/frontend-api-contract.md`, `frontend/src/hooks/useChatMessages.ts`
— made by the user or another agent, not by the auditing session.

Rules:
- Re-run `git status --porcelain` before trusting ANY snapshot of the tree.
- Foreign uncommitted changes are untouchable — never "repair" test failures caused by them,
  never fold them into your own work.
- When they affect files your audit cited line numbers against (auth.py), say the citations
  are against HEAD and the tree may differ.

## Verifying a git-level change (`.gitignore` / markdown) ≠ running the full suite

The full backend suite runs against the shared live Neo4j, is red at HEAD (3 seed-drift
failures, documented baseline), and would exercise whatever in-flight uncommitted work sits
in the tree. The correct gate:

```bash
git check-ignore -v <path>        # rule matched (e.g. .gitignore:62:docs/internship-report/)
git status --porcelain            # ignored dir vanishes from untracked listing
git diff --check -- <files>       # whitespace clean
git diff --name-only              # prove ONLY the intended files changed
```

Plus a targeted pure-unit pytest subset that imports neither the app nor the changed files:
`test_spoiler_policy.py` + `test_revision_models.py` + `test_user_content_models.py` →
51 passed in 0.26s, no DB, no app import (conftest is sys.path-only; verify before relying
on this). Report exactly what that proves (untouched code paths intact) and what it cannot
prove (gitignore rules, in-flight work) rather than claiming a suite-green.
