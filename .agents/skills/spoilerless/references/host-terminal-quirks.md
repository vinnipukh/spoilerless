# Host & Terminal Quirks — Windows/MSYS (HD Graf)

Verified 2026-08-12 while running the PROB-09 #81 pass. These cost repeated
failed tool calls in one session; check here before retrying anything.

## Repo path case matters (biggest time-sink)
- Canonical path: `C:\Users\arhan\PyCharmProjects\hdgrafcehennemi` — **capital `P`**
  in `PyCharmProjects`.
- Shell builtin `cd` case-folds on MSYS, so `cd /c/Users/arhan/PycharmProjects/...`
  (lowercase p) *works*.
- Native Windows tools resolve strictly: `git -C /c/Users/arhan/PycharmProjects/...`
  → `fatal: cannot change to '...': No such file or directory`.
- When a command unexpectedly fails to find the repo, run `pwd` and copy the
  casing it reports — don't guess.

## Terminal tool false-interrupt marker
- A foreground command can return `[Command interrupted]` with exit code 130
  while its output is **real and complete** (observed even on `echo x`).
- Trust the output; do NOT re-run a command just because of the marker.
- The marker also appears spuriously after otherwise-successful multi-line
  commands — read the stdout, ignore exit_code 130 when output is present.

## docker CLI blocks when the engine is down
- Once Docker Desktop dies mid-session, ANY foreground `docker ps` blocks the
  whole command until the terminal timeout kills it (no output at all).
- Relaunch: launch the exe directly as a background process:
  `"/c/Program Files/Docker/Docker/Docker Desktop.exe"` (background=true).
  `cmd.exe /c start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"`
  reported LAUNCHED but spawned nothing (verified: tasklist showed no docker
  processes).
- The launcher process exits after ~40s ("backend process exited") — that is
  normal; the engine may still be booting. Probe the daemon with a BOUNDED
  check (short `timeout` on the subprocess) instead of a foreground loop —
  a loop containing `docker ps` blocks the whole loop.
- Container: `hdgraf-neo4j` on `neo4j:5-community`, port 7687, creds per
  `scripts/env-local.sh`. `source scripts/env-local.sh && unset PYTHONPATH &&
  .venv/Scripts/python.exe -m pytest ...` for backend tests.

## Content search routing
- `search_files` can fail with an IO error on `C:\...` absolute Windows paths
  (rg can't resolve them in this MSYS setup). Terminal `grep -rn "<pattern>"`
  with an MSYS path (`/c/Users/...`) works reliably.
- For file-list/dir discovery, `find`/`ls` via terminal is the safe default.
