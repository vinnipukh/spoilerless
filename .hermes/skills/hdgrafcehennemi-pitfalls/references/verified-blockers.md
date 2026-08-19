# Verified Blockers — hdgrafcehennemi

Runtime-verified issues found during read-only reviews. These are confirmed
crashes (executed, not guessed); treat as top-of-list when the touched file
comes up in a task.

## BLOCKER: retrieval/pipeline.py missing ProgressService imports (verified 2026-08-11)

`spoilerless/app/retrieval/pipeline.py` references `ProgressService` and
`ProgressNotFoundError` (lines ~595 / 598 / 626) but imports neither — the only
services import is `from spoilerless.app.services.change_set import
ChangeSetService` (line 56).

- Verified: `RetrievalPipeline(FakeDB())` → `NameError: name 'ProgressService'
  is not defined`. `services/chat.py:193` masks this at the only production
  construction site by always passing `progress_service=`, so the default
  constructor path is broken but unreached.
- Latent half: `except ProgressNotFoundError:` at pipeline.py:626 is evaluated
  whenever `ProgressService.resolve` raises — i.e. the documented RAG-01
  no-progress fail-closed path (empty visible set, no 500) actually 500s with
  NameError. Except-clause names are resolved at handler time, so this stays
  hidden until that exception path fires.
- Fix: `from spoilerless.app.services.progress import ProgressService,
  ProgressNotFoundError`.

## How the verification was run (repo context)

- Ad-hoc Python: `./.venv/Scripts/python.exe -c "..."` FROM THE REPO ROOT so
  the `spoilerless` package resolves. Bare `python`/`python3` outside the venv
  give `ModuleNotFoundError: No module named 'spoilerless'`.
- Check name binding: `import spoilerless.app.retrieval.pipeline as p;
  'ProgressService' in dir(p)` → False.
- Exercise the path with a stub: `class FakeDB: pass;
  RetrievalPipeline(FakeDB())` → NameError confirmed.
