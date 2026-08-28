# Phase 9 plan verification results (plan-checker pass, 2026-08-05)

Verdict: `## ISSUES FOUND` — 2 WARNINGs, no blockers. All 18 plans pass
`verify.plan-structure` (`valid:true`, zero errors/warnings, correct
task_count and per-task hasFiles/hasAction/hasVerify/hasDone).

## Computed wave map (authoritative execution order — from depends_on DAG)

`gsd-tools.cjs query phase-plan-index 09-feature-expansion-full-audit-remediation`:

```
0: [09-01]            1: [09-02, 09-03, 09-06, 09-07, 09-15]
2: [09-04, 09-09, 09-16]   3: [09-05, 09-08, 09-10, 09-17]
4: [09-11, 09-18]     5: [09-12]   6: [09-13]   7: [09-14]
```

14 declared-vs-computed wave warnings. Notably the three operator plans
**09-16/09-17/09-18 declared `wave: 5` but compute to 2/3/4** because
09-16 depends only on 09-15: the "final operator wave" is NOT final in
execution order. If the operator push/CI/rename (09-16) and destructive
reseed/sweep (09-18) must truly run last, 09-16's `depends_on` must name the
last autonomous plan(s) (e.g. add 09-14), dragging the chain to the end.
See `gsd-workflow-overlays` → `references/plan-checking-wave-dag.md`.

## The two WARNINGs (pasted for the revision planner)

- **W1 (wave metadata drift):** declared `wave:` disagrees with the DAG on
  14 plans (all except 09-01, 09-03, 09-06, 09-10). Execution order is still
  correct (DAG-driven); re-sync the declared fields to the computed map above.
- **W2 (09-15 under-constrained):** 09-15 (docs) declares "sequenced AFTER
  all code plans so the docs describe the shipped state" and its Task 1
  inventories "the phase-9 routes (path, export, share)", but
  `depends_on: ["09-01"]` schedules it in computed wave 1 — before the
  path/export routes (09-11) and share routes (09-12) exist. Fix:
  `depends_on: ["09-01", "09-11", "09-12"]` (or `["09-14"]`), then re-sync wave.

## Verified in-tree facts (used to judge plan claims)

- **#42 already fixed:** `backend/app/services/auth.py` has the lazy
  `from google.auth.transport import requests as google_requests` inside the
  function scope, so `except google.auth.exceptions.TransportError` no longer
  NameErrors. Plan 09-02 is test-only regression lock (PROB-14/23) — correct.
- **Env files gone:** `backend/.env` and `frontend/.env.local` absent; only
  root `.env` exists. PROB-30 = envDir + equality check only, NOT deletion.
- **ci-smoke-test branch gone:** not in `git branch -a`; 09-16 Task 1 pushes
  local main directly (matches RESEARCH Open Q3).
- `backend/` still exists — the 09-01 `git mv backend spoilerless` rename has
  not executed; later plans correctly reference post-rename `spoilerless/`
  paths (D-12 sequencing).
- PROBLEMS.md numbering: **#30** = "minor symptomatic details" group (includes
  the requirements.txt-dup note — 09-01 deletes `backend/requirements.txt`
  citing #30, correct); **#55** carries a FACT-CHECK correction (frontend
  client id IS populated; PROB-30 is cleanup, not a bug fix — 09-05 honors
  it); #46/#47/#48/#49/#50/#51/#52/#53/#56/#57 map to PROB-22..32.

## Decision-coverage tool false-negatives (Phase 9)

`check.decision-coverage-plan` reported D-01/D-02/D-13/D-14 "uncovered" — all
four are substantively honored: REQUIREMENTS.md extended with PROB-22..32
(D-01), plans cite #NN finding numbers (D-02), no UptimeRobot creation plan
exists — only a monitor *rename* inside 09-16 (D-13), carry-overs folded into
09-08/09-16/09-17 (D-14). Text-match-only gate; do not block on it.

## Zero-cost / dependency audit (all honored)

- Sole new dependency: `cytoscape-fcose@2.2.0` (09-14, pinned, legitimacy-gate
  noted). `fuse.js`/`jspdf` appear only in prohibitions with grep gates.
- Chat/LLM verification is FakeLLMProvider-only (09-06 prohibition
  NO-LIVE-LLM-SPEND); path route calls the executor directly, no LLM loop.
- CI additions (pip-audit/npm audit, artifact upload) are scanner tooling, not
  runtime deps; 09-15 image self-hosting is a content task.
- All 45 req IDs covered: PROB-01..32, FEAT-01..10, FEAT-11, DOCS-04,
  REBRAND-01 (plus phase-8 carry-over IDs AUTH-03/SEC-03/INFRA-02/OPS-01 on
  the operator plans, which is expected).
