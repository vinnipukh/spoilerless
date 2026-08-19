# Frontend regression diagnostics (PROB-09/#61, 2026-08-11)

## Radix Select swallows re-selected values
Programmatically pre-setting a Radix Select/combobox value makes a later click
on THAT same option a silent no-op — `onValueChange` does not fire for the
currently-selected value.

Real case: `switchSeries` pre-set `viewAsOfOrder=1` → the episode selector
displayed S01E01 → the user's first click on S01E01 never dispatched
`handleEpisodeSelect` → ConfirmAdvanceModal never opened → App.test failed
"Unlock S01E01?" / "Yes, unlock episode" not found.

Fix pattern: keep the programmatic value `null`/absent until the user genuinely
selects (fail-closed empty state beats pre-selection). `switchSeries` now resets
boundary to `null`; the first episode click then fires normally through the
unlock flow.

Suspect this when: tests fail "modal never opens after clicking an option" and
a navigation action pre-selected that same option beforehand.

## Attribute regressions BEFORE debugging blind
With uncommitted changes: `git stash push <files>` → run failing suite at HEAD.
Green at HEAD = your change caused it (or the ledger's diagnosis is wrong).

TENTH-pass ledger blamed "App.test mock lacks switchSeries" — false:
`App.test.tsx` never mocks `useWatchProgress`; the real hook runs with
stubbed `fetch`. The mock-diagnosis was a guess, not a verification. Check the
test file's `vi.mock` list before trusting a ledger claim about mocks.

## CRLF breaks big multi-line patches
Windows checkout = CRLF (LF→CRLF warnings on every git touch). A 20+ line
`old_string` with em-dashes/unicode fails fuzzy match. Use small unique
single-hunk patches; they apply cleanly. Prefer patching by unique short
anchors (one title line, one assertion line).

## D-20 static scan tolerates query refactors
`test_story_sensitive_query_constants_are_boundary_gated` asserts each story
query constant CONTAINS `visible_from_order IS NOT NULL` and
`$visible_until_order` — no exact-string equality. Fragment-builder refactors
(f-string/concat over literal var names) pass the scan. No exact-string
assertions exist on query constants anywhere; restructure freely.

#62 placement: `visible_claim_where()` / `claim_projection()` live in
`spoiler/filter.py`; `retrieval/tools.py` imports them (no cycle — filter.py
imports nothing). Keep GRAPH_SUMMARY_COUNTS' EXISTS-subquery structure when
refactoring; the claim var stays `claim`.
