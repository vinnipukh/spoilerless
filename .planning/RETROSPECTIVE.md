# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.1 — MVP (supersedes v1.0, adds Phase 6 GraphRAG chat)

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

## Milestone: v1.3 — Production Deployment & Access Hardening

**Shipped:** 2026-08-14
**Phases:** 3 (8, 9, 10) | **Plans:** 37 | **Timeline:** 2026-08-04 → 2026-08-14 (10 days)
**Commits:** 285 | **Files:** 472 changed (+62,540 / −8,544)

### What Was Built
- Live zero-cost production deployment: Render + Vercel + Neo4j AuraDB Free + Upstash Redis, email allowlist, admin role, BYOK LLM chat, hardened cookies/CORS/CSRF/rate-limits, Redis graph-cache with write invalidation, GitHub Actions CI, UptimeRobot monitoring
- Full audit remediation: all 45+ PROBLEMS.md findings resolved, `hdgrafcehennemi` → `spoilerless` rebrand, 10 new features + FEAT-11 second-brain touches
- Deterministic test infrastructure: scratch-series isolation, drift-agnostic seed asserts, zombie sweep, CI DB-pollution gate — suite no longer mutates the live DB
- Narrative visualization redesign: library-neutral DTO, 6 projections, four-view hierarchy, Episode Overview variants, semantic expansion, GraphRAG Answer Graph, benchmark harness
- GAP-1 wiring closure: frontend calls the Phase-10 projection/expansion/graphrag-focus routes end-to-end

### What Worked
- The single pure resolver seam (`spoiler/app/spoiler/policy.py::resolve_effective_boundary`) made the Phase-10 projection redesign provably safe — one fail-closed function, audited once, reused across every channel.
- Zero-cost constraint held with an explicit cost story per feature: BYOK = user pays for chat; the blocked UAT row was recorded, not silently deferred.
- The milestone audit caught the real integration gap (frontend never calling Phase-10 routes) BEFORE close — the fix (260814-viz) shipped inside the milestone window instead of leaking into v1.4.
- Scratch-series + teardown fixtures killed the live-DB pollution class permanently (09-08) — the Phase-8 deferred item became stale debt, not recurring pain.

### What Was Inefficient
- GAP-2: REQUIREMENTS.md Phase-9 checkboxes stayed `[ ]` despite a passed 40/42 verification — the same paperwork-drift class flagged in v1.1's retrospective repeated, and had to be fixed inline at close.
- GAP-3: OpenAPI inventory prose drifted to 50/37 while the live surface was 52/39; POLISH-03's stale-wording grep didn't cover exact count strings.
- The audit's original verdict was `gaps_found` → required a post-closure re-audit (audit → fix → re-audit cycle) rather than a single clean pass.
- STATE.md frontmatter reported 67% / "In Progress" during the last plan while the phase was actually complete — ledger lag behind the working tree.

### Patterns Established
- Milestone audits earn their cost when they check *wiring* (any exported API function with zero frontend callers? any prop only set in tests?) — not just requirement checkboxes.
- Docs count-sweeps must grep exact numeric strings ("52 operations / 39 templates"), not just prose wording.
- Live-DB test determinism is a solved problem: scratch series + teardown fixtures + drift-agnostic asserts; never assert exact global node counts.
- Deferred/debug debt tracking needs a RESOLVED marker when the fix lands elsewhere — stale "open" rows resurface in `audit-open` at close.

### Key Lessons
1. Traceability checkboxes must be maintained per-phase, not at close — GAP-2 is v1.1's lesson #2 repeated; the archive is only as truthful as the table it captures.
2. A single pure enforcement seam beats N call-site checks — invest in the resolver once and every new feature inherits the guarantee.
3. Zero-cost is enforceable when every feature names its cost story and blocked items are recorded with evidence, never quietly dropped.

### Cost Observations
- Sessions: multiple (AFK chains + parallel subagents per phase)
- Notable: recorded plan-level tokens sum to ~183k across 37 SUMMARYs (partial — many plans lack the field); heavy use of delegated executors kept orchestrator context lean through a 285-commit window.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.1 | multiple | 8 | Established backend-authoritative spoiler filtering as the load-bearing invariant; closed with a phase 6 gap-closure loop (UAT → diagnose → plan → execute → re-verify) and a security audit that caught an unplanned, unreviewed feature. |
| v1.3 | multiple | 3 | Shipped a real zero-cost deployment; milestone audit (with wiring checks) caught the frontend integration gap pre-close; PROBLEMS.md numbered-pass ledger drove audit remediation; deterministic scratch-series test isolation ended live-DB pollution. |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|--------------------|
| v1.1 | 345 backend + 173 frontend | Not tracked as %, but 342/345 backend and 173/173 frontend passing at ship (3 pre-existing-debt failures) | 0 new production dependencies beyond `httpx` for phase 6 |
| v1.3 | 142 backend offline + 400 frontend at close (full gate: 11/11 chunks, 388→400 frontend) | Coverage audit 98/98 source ids (parser-verified); benchmark 0 schema/0 hard-gate failures | Stack additions locked to Redis (Upstash) + hosted targets; no frontend runtime deps added for Phase 10 |

### Top Lessons (Verified Across Milestones)

1. Verify UI fixes live (browser) before committing — code-only review missed a real collision that live testing caught in one screenshot.
2. Features that skip the plan/threat-model process are the ones that slip past every automated gate — the security audit is the last line of defense, not a formality.
3. Requirement-checkbox and ledger hygiene must be enforced continuously — both v1.1 and v1.3 hit stale-traceability issues at close despite green code.
