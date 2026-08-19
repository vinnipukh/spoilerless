# GETTING-STARTED.md verification — 2026-08-10

Verified `docs/GETTING-STARTED.md` against the live repository and bounded startup probes. Artifact: `.planning/tmp/verify-GETTING-STARTED.json` (126 claims checked, 124 passed, 2 failed). **SUPERSEDED by the same-day RE-VERIFICATION section below — the two discrepancies were fixed by a surgical doc rewrite and the post-fix doc re-verified 85/85/0.**

## Confirmed verification recipe

1. Read the doc with line numbers and inspect `pyproject.toml`, `.env.example`, `docker-compose.yml`, `frontend/vite.config.ts`, `frontend/package.json` + lockfile, backend config/setup/main, and UI/API implementation files named by behavioral claims.
2. Validate package prerequisites from committed metadata: Python requirement from `pyproject.toml`; Node constraint from `package-lock.json`'s installed `jsdom` entry, not only top-level Vite metadata.
3. Exercise cheap bounded paths: `uv sync --dry-run`, clean-project module imports, `npm install --dry-run --ignore-scripts`, backend/frontend startup, `/health`, `/api/series`, and an anonymous graph request. Stop servers and verify ports close afterward.
4. Distinguish repository/document failures from host setup state. A stopped Docker daemon does not make a correct Compose instruction a documentation failure; validate Compose syntax/config and record only code/doc mismatches in `failures`.
5. Validate the JSON invariants before returning: checked > 0; passed + failed = checked; `len(failures) == failed`; every failure has `line`, `claim`, `expected`, `actual`.

## Live discrepancies found

- `docs/GETTING-STARTED.md:116` says visitor mode hides write controls. `App.tsx` passes `readOnly={isVisitor}` to `GraphCanvas` but omits it from `DetailPanel`; `DetailPanel` defaults `readOnly=false`, so Notes/History and relationship/note write affordances remain visible even though backend auth blocks writes.
- `docs/GETTING-STARTED.md:120` says moving backward asks for confirmation. `useWatchProgress.requestChange` treats `nextOrder <= watchedThroughOrder` as an immediate view-only update and explicitly does not open the confirmation modal.

## RE-VERIFICATION (same day, post-fix) — doc now ACCURATE

A surgical doc rewrite fixed both discrepancies (working tree, uncommitted at re-verify time). The re-pass re-derived EVERY claim from the current doc — **do not reuse the baseline 126 count**: claims were rewritten, and the re-pass enumerated 85 claim clusters → **85 checked / 85 passed / 0 failed**, artifact `.planning/tmp/verify-GETTING-STARTED.json` overwritten. Run `git diff docs/GETTING-STARTED.md` first to see exactly which claims changed; re-check each rewritten claim with file:line evidence; keep the JSON invariants.

Key evidence anchors for the previously-failed claims (verified live):

- **Visitor (line 116)**: `App.tsx` STILL omits `readOnly` on `DetailPanel` (lines 557-568) → `DetailPanel` defaults `readOnly=false` (`DetailPanel.tsx:193/476`); Notes/History `TabsTrigger`s gated on `!readOnly` (`:717-718`) so they render; note Edit/Delete (`:207`) + Create Relationship (`:793`) visible to visitors. Chat hidden: `App.tsx:466/570/601`. Canvas write controls: `App.tsx:539 readOnly={isVisitor}`. Progress local to tab: `useWatchProgress({persist: !isVisitor})` (`App.tsx:117`; `useWatchProgress.ts:170-174` never POSTs, never opens modal). Anonymous reads pinned at order 1: `graph.py:82 requested = 1 if user is None`. Backend rejects writes: every `user_content.py` write route takes `CurrentUserDependency`.
- **Backward episode (line 120)**: `useWatchProgress.ts:200-205` — `nextOrder <= watchedThroughOrder` → immediate view-only update + awaited view-only POST, no `pendingChange`/modal, never lowers `watchedThroughOrder`.
- **Other rewritten claims re-verified**: BYOK localStorage-only + `X-LLM-*` headers (`byok.ts`, `chat.ts:41/87`); LLM precedence stored `:AppSetting {key:'llm'}` → `LLM_*` env incl. enabled switch (`chat.py:148-155`); candidates auth (ingest=any user `candidates.py:144`; list/get anonymous + required boundary `:166/:195`; edit/approve/reject admin `:346/:234/:294`); change-set apply admin (`change_set.py:116`); LLM settings admin (`settings.py:36/50`); `--project spoilerless` commands resolve; compose `NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-change-me}` + healthcheck + `./neo4j_data:/data`; jsdom 30.0.1 engines `^22.22.2 || ^24.15.0 || >=26.0.0` vs vite `^8.1.1`/eslint `^10.6.0`; no `frontend/.env.local`; `envDir: '..'`; proxy `127.0.0.1:8000`; pyproject has no build-system/`tool.uv.package`; seed ids `series_dexter` + `dexter_s01e01..03`.

## Confirmed anchors

- Remote/clone URL remains `https://github.com/vinnipukh/hdgrafcehennemi.git`.
- Python `>=3.13`; lockfile `jsdom` 30.0.1 requires Node `^22.22.2 || ^24.15.0 || >=26.0.0`.
- Frontend loads root `.env` via `envDir: '..'`; local proxy target is `http://127.0.0.1:8000`; no `frontend/.env.local` exists.
- Setup module path and backend/frontend startup commands resolve; health returned 200 with service `spoilerless-backend`; frontend returned 200.
- Anonymous graph request with requested boundary 3 returned effective/visible boundary 1, confirming fail-closed visitor reads.
