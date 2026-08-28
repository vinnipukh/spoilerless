# GSD progress/execute on Windows + operator-wave handoff

Running `/gsd-progress` / `/gsd-execute-phase` in the Hermes TUI (bash on Windows).

## gsd-tools.cjs invocation (MSYS path gotcha)

`$HOME/AppData/...` in git-bash expands to `/c/Users/...` — node rejects it
(`Cannot find module 'C:\c\Users\...'`). Always pass a Windows-style path:

```bash
GSD_TOOLS="C:/Users/arhan/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs"
gsd_run() { node "$GSD_TOOLS" "$@"; }
```

No repo-local `gsd-core/` — the shim lives in the hermes home, not the repo.

## Useful queries

```bash
gsd_run query init.progress          # phases, current, counts, verification status
gsd_run query progress.bar --raw     # bar, e.g. [███████░░░] 24/26 plans (92%)
gsd_run query state-snapshot         # decisions/blockers/session
gsd_run windows status --raw         # open/waived ledger (jq .ledger.open_count)
gsd_run query audit-uat --raw        # verification debt; .summary.total_items/files
gsd_run query phase-plan-index <N>   # per-phase waves/incomplete/blocked_by
```

`query summary-extract <path> --fields one_liner` returns `one_liner: null` for
this project's SUMMARY.md files (nonstandard frontmatter) — fall back to
`head -40` on the file.

## Route 0 resume invariant

`/gsd-progress` (no flags) scans ALL phases for plans-without-summaries and
routes to `/gsd-execute-phase <N>` for the LOWEST such phase — even when
STATE.md's current_phase already points past it. Expected: resume Phase N.

## Operator-wave plans (autonomous:false, checkpoint:human-action)

Remaining plans in the final wave are operator-touch: no executor dispatch.
Tell the user EXACTLY what they must do, in order, before running live checks:

1. **Google OAuth consent screen**: if the OAuth app is in *Testing* mode,
   test accounts must be added to Test users in Google Cloud Console — else
   they get no ID tokens at the live app. ("auth token stuff" = this.)
2. **Render dashboard → service → Environment**: add `ADMIN_EMAILS`
   (comma-separated) + `REDIS_URL` (Upstash rediss://, never in git).
   Auto-deploy on env change; confirm `curl https://api.spoilerless.net/health` = 200.
3. Operator sign-off gate before any destructive live-DB op (reseed/sweep):
   dry-run counts first, then explicit approval.

Live `/health` `service` field is the BUILD MARKER: `spoilerless-backend` = new
build, `hdgrafcehennemi-backend` = stale. Deploys fail silently on the old
start command override (`backend.app.main:app`) while /health stays 200.

## Stale .continue-here.md

Phase `.continue-here.md` from a mid-phase crash can be WEEKS stale (old HEAD,
old current_state) while the phase is actually 16/18 done. Still answer its
blocking anti-patterns (workflow gate), but cross-check counts against
`init.progress` before trusting its `<remaining_work>`/`<current_state>`.
