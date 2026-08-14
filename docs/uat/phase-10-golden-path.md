# Phase 10 UAT — Golden Path Checklist

**Milestone:** v1.3 | **Phase:** 10 polish-finishing-touches (POLISH-02)
**Environment:** local stack (vite :5173 → uvicorn :8000 → spoilerless-neo4j container), operator-approved hands-on session
**Date:** 2026-08-13
**Operator:** product owner (user) — approval recorded via blocking-human checkpoint reply `approved`
**Policy:** zero-cost — automated answer/focus behavior runs on FakeLLM; no paid LLM spend; no keys recorded.

| # | Scenario | Result | Evidence |
|---|---|---|---|
| 1 | Login (visitor + authenticated path) → series/episode select → Story opens bounded Episode Overview + Event Timeline rail | ✅ PASS | Operator hands-on; automated: App.test.tsx four-tab suite (32 tests) + 392-test full frontend suite |
| 2 | Characters tab — Character Network / Local Neighborhood; camera preserved across views | ✅ PASS (re-verified 2026-08-14 after 260814-viz wiring) | Operator hands-on; Characters tab now fetches the `character_network` projection (App.test.tsx wiring test); GraphCanvas/useSceneState suites green |
| 3 | Evidence tab — Investigation / Evidence Chain layered Claim → Evidence → Source; "Show in graph" explicit | ✅ PASS (re-verified 2026-08-14) | Operator hands-on; Evidence tab now fetches the `investigation` projection; EvidenceChain surface tests green |
| 4 | Advanced tab — Full Graph + debug labels | ✅ PASS | Operator hands-on; debugLabels test green (GraphCanvas.test.tsx) |
| 5 | BYOK chat contract (settings masking/headers/response handling) | ⏸ BLOCKED (operator-touch) | No zero-cost provider key approved at UAT time; automated chat-llm chunk green on FakeLLM (10-09 full gate). External-provider call requires an operator-approved zero-cost key — recorded, not deferred silently |
| 6 | Notes + export | ✅ PASS | Operator hands-on; DetailPanel readOnly + export tests green |
| 7 | Search / path / focus | ✅ PASS | Operator hands-on; NodeSearch/PathFinder suites green |
| 8 | Expansion → collapse/undo (no global relayout) | ✅ PASS (re-verified 2026-08-14 — was NOT wired at first approval; audit GAP-1) | Expand menu (7 keys) wired to `/graph/expand` + delta merge + Undo/Collapse (App.test.tsx expansion flow test); useSceneState history tests + GraphCanvas no-relayout tests green |
| 9 | Answer Graph open → close restores camera/selection/expansions/timeline | ✅ PASS (re-verified 2026-08-14 — graphrag_focus fetch was NOT wired at first approval; audit GAP-1) | Answer Graph now fetches `graphrag_focus` with citation focus ids (App.test.tsx wiring test); CLOSE_TEMPORARY snapshot tests (filters + active view) green |
| 10 | **Episode 2 → Episode 1 spoiler disappearance** (mandatory leak check) | ✅ PASS | Operator hands-on; boundary fail-closed matrix (spoiler policy + projection suites) green |
| 11 | Event Timeline rail resize (drag left edge / keyboard) — quick task 260813-wyp | ✅ PASS | Operator hands-on; 4 resize tests green |
| 12 | Graph Filters settings-style panel + scrolling — quick task 260813-fil | ✅ PASS | Operator hands-on; GraphFilterPanel.test.tsx (5 tests) green |

## Responsive / Accessibility / Restoration backstop rows

| Row | Check | Result | Evidence |
|---|---|---|---|
| UI-RESP-01 | Desktop/tablet/narrow composition, horizontal top tabs, no three-way squeeze | ✅ PASS | Operator hands-on (local widths); component tests for one-primary-region (max-sm) |
| UI-GESTURE-01 | Touch pan/zoom/tap; Inspector half/full sheet toggle | ✅ PASS | Operator hands-on; DetailPanel sheet tests |
| UI-TEXT-01 | Long evidence/notes/source wrapping; no horizontal page overflow | ✅ PASS | Operator hands-on; long-text copy tests |
| UI-A11Y-01 | Keyboard focus; Escape close + return focus; readable node access; role=switch filter toggles | ✅ PASS | Operator hands-on; DetailPanel Escape/close tests + switch role tests |
| UI-DENSE-01 | Advanced graph overflow | ✅ PASS | Operator hands-on |
| UI-IMAGE-01 | Episode-safe image fallback | ✅ PASS | Operator hands-on; DetailPanel fallback tests (260813-gao fix verified) |
| UI-RESTORE-01 | Answer Graph/Evidence close restores prior scene | ✅ PASS | Operator hands-on; snapshot restoration tests |

## Notes

- Screenshots: no captures were taken during this session; evidence is operator-observed behavior plus the automated suites named per row. Screenshot captures can be added later without re-running the checklist.
- BYOK chat row is the only blocked item: requires an operator-approved zero-cost provider key (no paid LLM spend allowed). The rest of the chat surface (retrieval, FakeLLM answer path, focus contract) is covered by the automated chat-llm chunk and test_visualization_graphrag.py.
