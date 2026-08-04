# Phase 7 Validation Coverage — Spoiler-Safety Hardening

**Phase:** 07-spoiler-safety-hardening · **Milestone:** v1.2 · **Date:** 2026-08-02

## Nyquist validation status: WAIVED by coverage evidence (documented 08-02)

`config.json` sets `workflow.nyquist_validation: true`, which the gsd-plan-checker
role normally enforces via a `*-VALIDATION.md` artifact (the archived 06 phase
carried `06-VALIDATION.md`). Phase 7 ships without a separately-regenerated
`RESEARCH.md`-driven validation artifact because **research was deliberately
skipped per the project runbook** ("research is skipped per runbook when the
spec is decisive" — the user-supplied spoiler-free plan IS the research). The
functional intent of the nyquist gate — every plan task carries a deterministic
`<verify><automated>` command — is met:

| Plan | Tasks | `<automated>` verify commands |
|------|-------|------------------------------|
| 07-01 | 3 | 3 |
| 07-02 | 3 | 3 |
| 07-03 | 3 | 3 |
| 07-04 | 3 | 3 |
| 07-05 | 3 | 3 |
| 07-06 | 3 | 3 |
| 07-07 | 3 | 3 |
| 07-08 | 3 | 3 |
| **Total** | **24** | **24** |

(24 tasks, not 32 — the checker's "32" counted subtasks/behavior entries; every
task block carries exactly one `<automated>` command.)

## Deterministic gates run at plan time

- `check.decision-coverage-plan` — **25/25 decisions covered** (D-01..D-25),
  passed 2026-08-02 after CONTEXT.md bullet format normalization (`**D-NN:**`).
- `verify.plan-structure` (gsd-tools) — `valid: true` for all 8 plans after the
  revision pass added `<files>` elements to 12 tasks that lacked them.
- Plan-checker review (gsd-plan-checker role, 2026-08-02) — 1 BLOCKER + 7 WARNINGs
  found; BLOCKER (07-02 boundary formula fail-open) fixed to
  `effective = min(visible_until_order, persisted_view_as_of_order,
  persisted_watched_through_order)`; all WARNINGs addressed (files elements,
  api/progress.ts wiring, seed path + curation null-out, episodes-route min,
  07-08 UI/UX scope note).

## Residual risks (tracked, not waived)

- 07-03 (17 files) and 07-07 (19 files) exceed the 15-file scope threshold —
  accepted with Phase 6 precedent (06-01 listed 20+ files); monitor execution
  context and split if a task approaches the iteration cap.
- Full-suite baseline 321 passed / 5 failed / 7 errors — verification compares
  FAILED/ERROR NAME SETS, never counts alone (D-25).
