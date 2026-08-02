# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-08-02
**Phases:** 8 (1, 2, 3, 4, 5, 6, plus inserted 03.1 and 05.1) | **Plans:** 35 | **Sessions:** multiple across 2026-07-28 → 2026-08-02

### What Was Built
- Spoiler-safe backend graph foundation (Neo4j + FastAPI) with fail-closed episode-boundary filtering
- Polished React/Cytoscape graph UI with a cinematic visual overhaul
- User notes and manual graph editing with canonical/user provenance separation
- Append-only revision history with inspect/revert
- Future-extraction preparation layer (candidate review workflow, source-connector contract)
- Full spoiler-safe GraphRAG chat agent: ten allowlisted retrieval tools, LLM provider abstraction, citation-grounded answers, and a typed two-stage ChangeSet propose/confirm/revert flow

### What Worked
- Backend-authoritative spoiler filtering as a structural invariant held cleanly through the entire GraphRAG chat addition — zero leakage found across UAT, verification, or security audit for Phase 6, because the boundary was enforced at the data-access layer from Phase 1 onward rather than bolted on later.
- The allowlisted-typed-tool pattern (no raw Cypher ever reaches the LLM) proved itself structurally sound under a dedicated prompt-injection test suite and an independent security audit — no threats were found in that surface.
- Delegating the phase-6 gap-closure loop (UAT → diagnose → plan → execute → re-verify) to background subagents kept the orchestrator's context lean across a very long session while still producing a fully-diagnosed root cause (not a guessed fix) for the stuck Stop-button bug.
- Live verification via the Claude-in-Chrome browser extension caught a real regression (moving graph controls to bottom-right collided with the resizable chat sheet) that pure code review would have missed — worth doing for any UI-adjacent fix before calling it done.

### What Was Inefficient
- Two consecutive UI fix attempts for the Legend/controls collision iterated on the wrong root cause (height cap, then wrong-corner relocation) before landing on horizontal separation — the first fix should have been verified live in the browser before committing, not after.
- Worktree-isolated debug/executor agents twice hit a stale worktree base (repeatedly resolving to an old `46d74ac` commit, 86 commits behind HEAD) — had to fall back to unisolated dispatch. This cost two wasted agent round-trips before working around it.
- The Settings feature (a substantial, unplanned addition — `/api/settings/llm`, full Settings UI) landed on the branch with no PLAN.md/SUMMARY.md/STRIDE entry anywhere in Phase 6, so it was invisible to every phase-gated review until the security auditor traced the implementation directly. This is exactly the kind of drift a phase's own gates are supposed to catch.
- `.planning/REQUIREMENTS.md` and `ROADMAP.md` prose both drifted out of sync with actual implementation state (17 RAG requirement checkboxes and 8 v0 requirement checkboxes were stale-unchecked despite verified implementations; Phase 3/4/5 formal `VERIFICATION.md` files were stale, missing, or never generated despite the features being functionally complete) — this wasn't caught until milestone close, forcing an `override_closeout` decision instead of a clean `verified_closeout`.

### Patterns Established
- When a fix to a shared UI element (buttons, panels, controls) is proposed, check what ELSE occupies that same screen region across all major UI states (chat open/closed, sheets open/closed) before committing — a fix that only considers the reported bug's immediate context can trade one collision for another.
- For subagent debug/executor dispatch: if a worktree-isolated dispatch fails a HEAD-base assertion once, don't just retry with a new base — the provisioning itself may be broken; fall back to unisolated dispatch for read-only or low-risk work rather than burning multiple retries.
- A feature that lands without a PLAN.md/threat model should be caught by the phase-close security audit, not discovered by accident — worth adding an explicit "any files changed with no corresponding PLAN.md in this phase?" check to the standard gap-audit flow.

### Key Lessons
1. Structural security invariants (no raw Cypher to the LLM, backend-authoritative visibility) are much more durable than per-feature reviews — invest in the invariant once, verify it holds, and new features built on top inherit the guarantee almost for free.
2. Requirement-checkbox and VERIFICATION.md hygiene needs to be enforced continuously, not caught at milestone close — a phase that's functionally done but whose paperwork lags creates exactly the kind of ambiguity that forces an override decision instead of a clean gate pass.
3. Any feature that introduces a new shared/global resource (like a single-row settings config) needs an explicit ownership-model decision recorded at plan time — "who can change this and who is affected" is not optional even for a single-user prototype, because it becomes a real vulnerability the moment auth exists.

### Cost Observations
- Sessions: multiple (exact count not tracked)
- Notable: heavy use of background subagents (doc writers, verifiers, debuggers, security auditor, code fixers) kept the orchestrating session's context usable across a milestone spanning 8 phases and 35 plans; the phase-6 security audit alone read 13 plan files + 13 summaries + ~20 implementation files in one dispatch rather than in the main thread.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | multiple | 8 | Established backend-authoritative spoiler filtering as the load-bearing invariant; closed with a phase 6 gap-closure loop (UAT → diagnose → plan → execute → re-verify) and a security audit that caught an unplanned, unreviewed feature. |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|--------------------|
| v1.0 | 345 backend + 173 frontend | Not tracked as %, but 342/345 backend and 173/173 frontend passing at ship (3 pre-existing-debt failures) | 0 new production dependencies beyond `httpx` for phase 6 |

### Top Lessons (Verified Across Milestones)

1. Verify UI fixes live (browser) before committing — code-only review missed a real collision that live testing caught in one screenshot.
2. Features that skip the plan/threat-model process are the ones that slip past every automated gate — the security audit is the last line of defense, not a formality.
