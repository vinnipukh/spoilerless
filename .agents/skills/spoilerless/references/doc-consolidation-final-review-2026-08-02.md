# Documentation consolidation final review — 238e973 (2026-08-02)

Independent read-only verification of the docs regeneration + consolidation
deliverable (commit `238e973` + uncommitted consolidation work). The repo is
now in its FINAL consolidated docs state — read this before touching any root
or `docs/` file.

## Final docs state (durable)

- `HD_GRAF_CEHENNEMI_CODING_AGENT_SPEC_V2.md` (5 lines) and `ROADMAP.md`
  (7 lines) are COMPATIBILITY STUBS: "Canonical document moved:
  [docs/PROJECT-SPEC.md] / [docs/ROADMAP.md]". Do not add requirements, status,
  or scope to the stubs. The ROADMAP stub also states `.planning/ROADMAP.md`
  is a separate GSD planning artifact — that distinction lives in the stub.
- Canonical spec: `docs/PROJECT-SPEC.md` — 13 sections; explicit status
  vocabulary (implemented / prototype target / future) at line 3; §11
  operating instructions, §12 prototype DoD, §13 current gaps/scope.
- Canonical roadmap: `docs/ROADMAP.md` — 11 sections; status legend
  (Complete / Partially complete / Future) in §0; Milestone 10
  (auth/settings/guarded ChangeSets) is post-original-roadmap; §11 maintenance
  rules. Historical corrections (e.g. stale `/api/graph?series_id=` route,
  "evidence links" → metadata/locators) are explicitly labeled inside the
  milestone sections.
- Audit artifacts live in `.planning/tmp/`: `doc-audit-onboarding.md`,
  `doc-audit-technical.md`, `doc-audit-consolidation.md` (ledgers),
  `doc-final-review.json` (final verdict artifact).
- Route inventory baseline unchanged: 32 path templates / 44 (method,path)
  operations, test-locked in `test_frontend_contract_doc.py` (asserts
  `len(...) == 44` and `len(EXPECTED_TEMPLATES) == 32`).

## Three-section independent verification methodology

For "independently verify final documentation state" tasks, do A/B/C and write
one JSON artifact (schema at the end).

### A — Diff coverage
`git diff-tree --no-commit-id --name-only -r <commit>` enumerates the owned
files. Map EVERY file to an explicit audit disposition (a ledger row, a stub
classification, or workflow-state-only for manifests). Report
`missing_disposition`; empty means full coverage. Re-verify ledger hunk counts
with the SAME diff settings the ledger used (pitfall below).

### B — Technical accuracy (residuals)
When a prior audit left a known list of N unresolved residuals, verify each one
as a doc-line ↔ source-line pair: grep the doc claim, then grep the live
source that must corroborate it (e.g. `provider.py` endpoints for Gemini
wording, `GraphCanvas.tsx` try/catch for conditional layout registration, the
Cypher query for boundary/edge-emission semantics, `settings.py`
`if update.api_key:` for whitespace-key truthiness). Sample a few extra
high-risk claims beyond the residual list: route tables vs `app.openapi()` and
the test-locked frontend contract, persisted-Episode boundary validation vs
the actual query, provider availability vs configured active provider.

### C — Losslessness
1. Heading map: `git show <rev>:<root-file> | grep -nE '^#{1,3} '` vs the
   canonical doc's headings — every root section/subsection must appear or be
   explicitly merged/linked. (Works for both `HEAD` and `HEAD^` revisions of
   the root files.)
2. Bullet-level spot checks on high-value blocks: DoD steps, operating rules
   (incl. the "every" rules), scope-boundary item lists, demo-story steps,
   milestone task/acceptance lists. Merging/grouping is lossless ONLY when the
   merged bullet names every original item or the delta is disclosed in prose
   (e.g. claim-edit demo step → "API workflow, no comprehensive review UI").
3. Links/anchors: resolve every `](...)` target file plus GitHub-style anchor
   slugs against the target's headings — run `scripts/check-doc-links.py`.
4. Stubs: canonical pointer correct, no stale content, do-not-edit wording.
5. Status-contradiction scan: current-vs-future contradictions should be
   prevented by an explicit status vocabulary/legend (PROJECT-SPEC line 3,
   ROADMAP §0). Phrasing like "Complete in source/configuration, runtime
   depends on services" (M1) or "disabled by default is configuration state,
   not missing implementation" (M9) is CORRECT handling, not a defect.

## Pitfalls (each cost real time this run)

- **Hunk-count mismatch is a diff-settings artifact, not a ledger error.**
  `git diff HEAD^ HEAD -- file | grep -c '^@@'` counts DEFAULT-context hunks;
  the ledgers counted `--unified=0` hunks. Observed: docs/API.md 2 default vs
  106 unified-zero; ARCHITECTURE 8 vs 140; CONFIGURATION 15 vs 44; frontend
  contract 13 vs 18; README 12 (same either way). Re-run with `--unified=0`
  before ever flagging a coverage discrepancy.
- **A spec-level doc need not contain literal IDs.** `series_dexter` appears
  in README/API/ARCHITECTURE/GETTING-STARTED/ROADMAP (route examples) but NOT
  in `docs/PROJECT-SPEC.md` — absence there is not a loss and not a missing
  content flag.
- **JSON artifact verification ≠ pytest.** The final-review artifact is a JSON
  data file; broad pytest is forbidden on this repo for read-only tasks (the
  suite live-seeds and mutates the shared Neo4j). The relevant verification is
  exact schema conformance — top-level keys, field types, `files_expected`,
  disposition-list length, and ALL issue arrays empty as the precondition for
  `passed: true` — run inline or via the OS-temp `hermes-verify-*` pattern
  (see gsd-docs-update). Report "no code changed; pytest inapplicable" — never
  claim suite green.
- `git status --short` after consolidation shows the 12 modified files + the
  two NEW untracked canonical docs (`docs/PROJECT-SPEC.md`, `docs/ROADMAP.md`);
  the audit ledgers are gitignored, so absence from `git status` is expected.

## Final-review artifact schema (`.planning/tmp/doc-final-review.json`)

```json
{
  "passed": true,
  "section_a": {"files_expected": 12, "files_with_disposition": ["<file> (<ledger> treatment)..."], "missing_disposition": []},
  "section_b": {"claims_sampled": 15, "factual_errors": [], "contradictions": [], "residuals_of_known_10": []},
  "section_c": {"spec_sections_checked": 48, "roadmap_sections_checked": 27, "links_checked": 121,
                "missing_content": [], "broken_links": [], "stub_issues": []},
  "summary": "PASS. ...",
  "_evidence_note": "optional context"
}
```
`passed: true` requires every issue array empty AND 12/12 dispositions.

## 2026-08-02 baseline (re-extract after any docs edit)

A: 12/12 files with dispositions (5 onboarding + 4 technical + 2 root
consolidation + 1 workflow manifest). B: 10/10 known residuals resolved, 15
claims sampled, 0 errors/contradictions. C: 48 spec + 27 roadmap headings
mapped; 121 links across 13 files, 0 broken; both stubs clean. All ten
residual fixes (Gemini endpoints, cose-bilkent fallback, user-edge endpoint
survival, provider availability vs active, series_dexter, Character/Claim-only
substitution, whitespace-key persistence, claim_id:null semantics, revision
positive-nonpersisted boundaries, frontend-contract route split) verified
against live source.
