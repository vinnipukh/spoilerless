---
phase: 10
slug: polish-finishing-touches
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-13
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Automated work must remain zero-cost/FakeLLM or fixture-based wherever possible. Never run tests against live Neo4j users or `series_dexter`.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest 9.1.1+, pytest-asyncio 1.4.0+, async mode `auto` |
| **Backend config** | `pyproject.toml`; tests under `spoilerless/tests/` |
| **Frontend framework** | Vitest 4.1.10+, Testing Library, jsdom 30.0.1 |
| **Frontend config** | `frontend/vite.config.ts`; setup `frontend/src/test/setup.ts` |
| **Quick backend run** | `uv run pytest spoilerless/tests/test_spoiler_policy.py spoilerless/tests/test_graph_api.py -q` |
| **Quick frontend run** | `cd frontend && NODE_ENV=test CI=1 npm test -- --run src/components/graph/GraphCanvas.test.tsx src/components/graph/graphElements.test.ts` |
| **Full backend run** | Phase 10 plan creates `scripts/run_phase10_backend_tests.py`: uniquely named Neo4j 2026.06.0 container + ephemeral volume, both alias families overridden, guaranteed cleanup; never developer/shared/Aura data |
| **Full frontend run** | `cd frontend && NODE_ENV=test CI=1 npm test -- --run` |
| **Static gates** | `cd frontend && npm run lint && npm run build` |
| **Estimated feedback** | Focused unit/contract checks < 120s; full suites sampled per wave |

## Sampling Rate

- **After every task commit:** run the task's focused backend or frontend command.
- **After every plan:** run all focused tests named by that plan.
- **After waves 1–4:** run the cumulative focused backend/frontend files named by completed plans; the isolated full backend runner does not exist until Plan 10-09.
- **After wave 5:** run full frontend Vitest after the coordinated view shell lands, plus cumulative focused backend tests.
- **After waves 6–7:** run cumulative focused cross-stack suites named by Plans 10-07/10-08.
- **Wave 8 / Plan 10-09:** provision the ephemeral Neo4j target and run the complete backend inventory, full frontend Vitest, lint, build, and diff gate. No earlier plan may use shared/Aura data merely to satisfy a “full wave” label.
- **Before `/gsd-verify-work`:** isolated backend pytest, frontend Vitest, lint, build, benchmark report, and UAT evidence must all be green/complete.
- **Max feedback latency:** 120 seconds for focused checks; long full-suite/database checks are wave gates rather than per-task gates.

## Per-Plan Verification Map

| Plan slice | Requirements | Threat Ref | Secure behavior | Automated evidence |
|---|---|---|---|---|
| Audit/baseline tracer | VIZ-03, VIZ-10 | T10-LEAK-01 | Fixtures contain only safe S01E01/cumulative S01E02 rows; no live DB | snapshot/schema checks and deterministic baseline command |
| Neutral DTO + boundary | VIZ-01, VIZ-02 | T10-BOUND-02 | Clamp/filter precedes projection and serialization | projection/policy/API pytest |
| Projection/cache | VIZ-03, VIZ-09 | T10-CACHE-03 | hard caps and cache dimensions prevent cross-view/boundary returns | projection/cache pytest |
| Cytoscape adapter/scene | VIZ-07 | T10-BOUND-04 | no hidden metadata or network fetch on zoom; no relayout on selection | adapter/reducer/GraphCanvas Vitest |
| Four-view UI/mobile | VIZ-04, VIZ-05 | T10-BOUND-05 | safe DTO-only rendering and accessible stable state | App/DetailPanel/timeline Vitest + responsive UAT |
| Expansion | VIZ-06 | T10-BOUND-06 | allowlist, hard max 25, no hidden totals | API pytest + reducer/adapter Vitest |
| Answer Graph/evidence | VIZ-08 | T10-FOCUS-07 | retrieval remains complete-safe; visible DTO bounded; scene restores | FakeLLM contract tests + restoration Vitest |
| Benchmarks/refinement | VIZ-10 | T10-BOUND-08 | in-memory deterministic data only | four required size reports |
| Closeout | POLISH-01..03 | T10-LEAK-09 / T10-LEAK-10 / T10-LEAK-11 | no shared live mutations; truthful shipped docs | full suites, lint/build, UAT, docs verification |

## Wave 0 Requirements

- [ ] `spoilerless/tests/test_visualization_projection.py` — neutral DTO, boundary order, bounds, omissions, indirect leaks.
- [ ] `spoilerless/tests/test_visualization_cache.py` — view/version/revision/user separation and Redis degradation.
- [ ] Safe checked-in S01E01 and cumulative S01E02 projection fixtures — no live `series_dexter` reads.
- [ ] `frontend/src/lib/visualizationAdapter.test.ts` — DTO adapters, label suppression, stable IDs.
- [ ] Scene reducer/hook tests — selection, camera, expansions, restoration.
- [ ] Deterministic benchmark harness/result schema for 30/50, 75/150, 150/400, 300/1000.
- [ ] `scripts/run_phase10_backend_tests.py` + mock-driven guard tests — provision/verify/clean one ephemeral local Neo4j target; reject developer/shared/Aura targets and alias-precedence bypasses.
- [ ] Responsive/FakeLLM UAT checklist with explicit shared-mutation prohibition; real BYOK is manual operator-only, masked, never recorded.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Narrative comprehension and A/B choice | VIZ-03, VIZ-10 | Clarity/crossings/comprehension require human judgment | Compare fixed S01E01/S01E02 variants with recorded metrics and select via Decision Log. |
| Mobile visual composition | VIZ-05 | Real viewport/touch and half/full sheet behavior | Verify scrollable top tabs; graph/timeline/Inspector are never squeezed together; touch and focus remain usable. |
| Golden path | POLISH-02 | Real OAuth/deployed interaction plus zero-cost chat contract | Login → series/episode → four views → BYOK settings/masking/transport with FakeLLM or operator-approved zero-cost provider only → notes/export → expansion → Answer Graph/Evidence Chain → Overview restoration → Episode 2→1 disappearance; include Dexter family, Doakes distrust, events/clues/cases. Never incur paid LLM spend. |
| Shipped-state documentation | POLISH-03 | Truth must be checked against deployed behavior | Verify README/root docs, API and architecture describe the actual routes, hierarchy, deployment and screenshots/links. |

## Validation Sign-Off

- [x] Every planned slice has an automated command or explicit Wave 0 dependency.
- [x] Sampling continuity prevents three consecutive implementation tasks without automated verification.
- [x] Wave 0 covers all currently missing projection/cache/adapter/scene fixtures.
- [x] No watch-mode flags are used.
- [x] Security/spoiler behavior has explicit threat references and safe evidence.
- [x] `nyquist_compliant: true` is set for plan checking; `wave_0_complete` remains false until execution creates the listed fixtures.

**Approval:** planning-ready 2026-08-13
