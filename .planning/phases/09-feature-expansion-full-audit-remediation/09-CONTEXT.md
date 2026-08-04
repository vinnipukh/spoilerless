# Phase 9: Feature Expansion & Full Audit Remediation - Context

**Gathered:** 2026-08-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Resolve every finding in `docs/PROBLEMS.md` (ALL 57 — the ledger now exceeds the
45 findings REQUIREMENTS.md was written against; #46–57 must be folded in as new
PROB requirements), ship the 10 new user-facing capabilities (FEAT-01..10) plus
FEAT-11 second-brain touches, rename the product/repo `hdgrafcehennemi` →
`spoilerless` (REBRAND-01), and align the three docs (DOCS-04). Also absorbs the
Phase 8 carry-over plans 09-02..09-08 (09-01 UptimeRobot is already LIVE — UAT
#11 passed; drop it). Builds on the deployed, access-hardened v1.3 app
(Phase 8 complete, verified 2026-08-05).

Requirements in scope: PROB-01..21 (existing, #1–45) + NEW PROB-22..32 mapping
#46–57, FEAT-01..10, FEAT-11, DOCS-04, REBRAND-01. POLISH-01..03 belong to
Phase 10, NOT here.

</domain>

<decisions>
## Implementation Decisions

### Problem-remediation scope — ALL 57 findings, folded
- **D-01:** Phase 9 targets every finding in `docs/PROBLEMS.md` (57 as of
  2026-08-05), not just the 45 REQUIREMENTS.md was written against. The
  planning step MUST extend `.planning/REQUIREMENTS.md` with new PROB entries
  for #46–57 before/when writing plans:
  - #46 → zombie AppUser/session sweep + candidate tests scratch-series-scoped + CI DB-pollution gate (folds 09-05)
  - #47 → real `ProductionGoogleVerifier` behavioral test (garbage token + MockTransport); wire-shape contract tests that do NOT mock the FE API client
  - #48 → `get_user_notes` results must actually enter the assembled context (add notes accumulator bucket in `retrieval/pipeline.py`; pass `retrieved["notes"]` to `assemble_context`)
  - #49 → one visibility-derivation rule shared by direct user-content API and ChangeSet apply (`max(episode order, current progress)` fail-closed, per FEATURE-RESEARCH framing)
  - #50 → stamp `created_by` on direct user-content API create paths too (not just ChangeSet)
  - #51 → ChangeSet revert keeps BOTH revision ids (`apply_revision_id` + `revert_revision_id`)
  - #52 → catch `JSONDecodeError` in `OpenAICompatibleProvider`; delete dead `detect_language`; cap/summarize replayed tool results
  - #53 → add `series_id` to SOURCES/EVIDENCE endpoint MATCH; fix `docs/DEVELOPMENT.md:50` command
  - #54 → context only, no code (ChangeSet + spoiler read-path are the strongest code; do NOT rework)
  - #55 → env consolidation: root `.env` + `envDir: '..'` in `vite.config.ts`, delete `backend/.env`, keep `VITE_` prefix for browser vars, startup/CI equality check for GOOGLE_CLIENT_ID vs VITE_GOOGLE_CLIENT_ID (note: the FACT-CHECK correction stands — the client id is populated; this is cleanup, not a bug fix)
  - #56 → fix `useWatchProgress.ts::requestChange` silent no-ops (lines 133/139) + mount-time hydration race; regression test for locked-episode click with failing view-only POST
  - #57 → graph canvas density overhaul (see D-02)
- **D-02:** `docs/PROBLEMS.md` is the canonical problem ledger; planning must
  read it in full and cite finding numbers per plan, never plan from
  REQUIREMENTS.md alone.

### Graph canvas density (PROBLEMS #57 + FEAT-11 filters) — FULL cluster-aware layout
- **D-03:** User chose **full cluster-aware layout** over the lighter filter-only
  path: replace the flat `cose-bilkent` pass with **cytoscape-fcose**
  (new dependency) using compound/cluster parent nodes driven by stable data
  keys (subplot/cluster tag or `Event.sequence_in_episode` bands). This is the
  fix for #57, not just FEAT-11's filter panel.
- **D-04:** Also ship: node-type/edge-type filter toggles (FEAT-11), zoom-based
  label culling, focus/neighborhood mode (reuse existing `faded`/
  `selected-dominant` classes via a focus reducer), deterministic layout
  (seed positions or cache per boundary so the graph doesn't re-scramble),
  edge bundling or opacity falloff.
- **D-05:** Update `GraphCanvas.test.tsx:200`'s `toHaveLength(11)` to the
  enriched S01E01 counts or make it count-independent.
- **D-06:** `GraphCanvas.tsx` is already a god-file (#18/#53) — planning should
  prefer extracting (layout config, filter state, focus reducer) over piling
  into it, but god-file decomposition itself stays out of scope (deferred in
  REQUIREMENTS.md).

### Test isolation (PROBLEMS #15, PROB-06, 09-05) — scratch-series + teardown, NOT Testcontainers
- **D-07:** User chose **scratch-series + teardown fixtures** over Testcontainers.
  Candidate/seed tests move to scratch `series_*` ids with teardown fixtures
  (matches the existing retrieval-test scratch-series pattern); one-time zombie
  sweep of 3,855 `:AppUser` + 21 expired `:Session` nodes (never delete real dev
  user `ae8a41b7-db96-40e8-b6c2-2e3c69aedb11`); CI gains a DB-pollution gate
  (PROB-06 / #14 / #15 / #46).
- **D-08:** Tests must never mutate the real `series_dexter` graph or real user
  rows; seed-idempotency assertions become order/state-independent where the
  ledger calls for it.

### FEAT-09 shareable snapshot link — snapshot-at-creation
- **D-09:** User chose **snapshot-at-creation**: the share token stores
  `series_id` + boundary + `created_at`; the read-only route reuses the SAME
  spoiler-filtering path as `api/graph.py` (never a second, looser code path).
  A link always shows exactly what was visible at creation.
- **D-10 (Claude's discretion, stated):** tokens revocable (delete = revoke),
  default 30-day expiry, random URL-safe token via stdlib `secrets`; new Neo4j
  label for share tokens; unauthenticated-but-token-gated route; frontend
  read-only route distinct from the authenticated shell.

### FEAT-05 export — Markdown only
- **D-11:** User chose **Markdown only** (zero new deps). Backend renders the
  visible knowledge (notes, claims, evidence) as Markdown; FE downloads a `.md`
  file. No jspdf/PDF.

### REBRAND-01 — spoilerless rename (locked in ROADMAP SC#0)
- **D-12:** Rename every user-visible and repo-level `hdgrafcehennemi`
  reference → `spoilerless`: package dirs, pyproject, docker-compose container
  name, service names, README, DEPLOYMENT.md, `/health` `service` field, UI
  title. Git history intentionally untouched; runtime/deploy names updated.
  Sequencing note: do the rename EARLY in the phase so later feature plans
  touch renamed paths, not the other way around.

### Carry-overs from Phase 8 (ROADMAP 09-01..09-08)
- **D-13:** 09-01 (UptimeRobot) is DONE — verified live, UAT #11 pass (free-tier
  false-downs during Render sleep = accepted cost, no plan needed).
- **D-14:** Remaining carry-overs are IN scope as plans: 09-02 (CI smoke fixes →
  main, confirm Actions green), 09-03 (admin-role live verification with
  `ADMIN_EMAILS` configured), 09-04 (`REDIS_URL` on Render + live 429/cache
  verification), 09-05 (seed-test pollution — folded into D-01/#46), 09-06
  (frontend lint 0-error — folded into PROB-08), 09-07 (full CI/CD: dependency
  scanning, artifact publication, staged promotion, branch protection),
  09-08 (full observability: centralized logs, metrics dashboards, incident
  runbook).

### Claude's Discretion
- Exact fcose layout tuning, compound-node cluster tags, focus-reducer shape.
- Share-token label name, exact expiry sweep mechanism.
- Series dashboard (FEAT-04): augment the existing dropdown (keep dropdown,
  add dashboard as entry point) unless evidence says replace — user did not
  override the ROADMAP "replacing/augmenting" ambiguity.
- Timeline view (FEAT-02) placement: tab alongside the graph vs alternative
  view — pick the tabbed approach consistent with the existing panel layout.
- Which remaining #46–57 items land in which plan wave.
- Exact `ALLOWED_EMAILS` value for 09-03 (operator supplies).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Problem ledger & features (user-attached, authoritative for this phase)
- `docs/PROBLEMS.md` — ALL 57 findings; canonical scope for PROB work. Read in FULL — REQUIREMENTS.md's 45-finding framing is stale.
- `docs/FEATURE-IDEAS.md` — brainstorm list (not commitments); source vocabulary for FEAT-01..10 + FEAT-11.
- `docs/FEATURE-RESEARCH.md` — per-idea dependency/file impact analysis; verified against the live tree. Zero-new-dep guidance drives FEAT decisions (D-03/D-11).

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — PROB-01..21, FEAT-01..10, FEAT-11, DOCS-04, REBRAND-01; MUST be extended with PROB-22+ for #46–57 (D-01).
- `.planning/ROADMAP.md` §Phase 9 — success criteria 0–6, carry-over plans 09-01..09-08.
- `.planning/STATE.md` — v1.3 position; Phase 8 closed 2026-08-05.

### Product/spec docs
- `docs/PROJECT-SPEC.md` §3 (non-negotiable invariants), §6 (visual language), §7 (GraphRAG constraints) — cited by FEATURE-IDEAS/FEATURE-RESEARCH as the guardrail for every feature idea.
- `docs/ARCHITECTURE.md` — live codebase architecture; DOCS-04 must make it match reality (route counts, ChangeSet capability, known-gaps section).
- `docs/API.md` — route counts stale (44/32 vs live 45/33); DOCS-04.
- `docs/DEPLOYMENT.md` — deployment truth for REBRAND-01 + 09-07/09-08.

### Codebase maps
- `.planning/codebase/STACK.md` — stack/versions (Python 3.13, React 19, Cytoscape).
- `.planning/codebase/TESTING.md` — test commands (`uv run pytest` from root, `NODE_ENV=test CI=1 npm run test`), live-DB test pollution hazards.
- `.planning/codebase/STRUCTURE.md`, `CONVENTIONS.md`, `CONCERNS.md` — module layout, conventions, known concerns.

### Prior-phase context
- `.planning/phases/08-production-deployment-automated-ci-cd/08-CONTEXT.md` — Phase 8 decisions (hosting, admin role, BYOK headers, rate limits) still in force.
- `.planning/phases/08-production-deployment-automated-ci-cd/08-VERIFICATION.md` — Phase 8 closeout; 09-02/09-03 carry-over evidence.
- `.planning/phases/08-production-deployment-automated-ci-cd/08-UAT.md` — 12 UAT rows; #4 (CI fixed-pending-ci-rerun), #6 (admin skipped), #11 (uptime live).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/retrieval/tools.py` — `find_path`, `get_character_context` and 10 other allowlisted tools; FEAT-06 (path finder) and the "character insight" idea expose these DIRECTLY via a route instead of only through the chat loop (FEATURE-RESEARCH's repeated pattern).
- `frontend/src/lib/byok.ts` — localStorage get/save pattern; FEATURE-RESEARCH says bookmark/theme features copy its exact shape.
- `backend/app/graph/filter.py` / `spoiler/filter.py` — the spoiler read-path is the strongest code; FEAT-09 MUST reuse it, never fork a second filter.
- `frontend/src/components/graph/GraphControls.tsx` — zoom/fit/reset; selection-driven actions (FEAT-06 path button) hang off it.
- Existing `faded`/`selected-dominant` Cytoscape classes — focus/neighborhood mode (D-04) wires a real focus reducer over them.
- `frontend/src/hooks/useWatchProgress.ts` — progress hook needing #56 fixes.
- `backend/app/domain/change_set.py` — 13-op typed union; #51 revision-link fix lives here/`graph/change_set.py`.

### Established Patterns
- Backend: FastAPI + Pydantic v2 strict models + Neo4j async driver; repo/service/API layering (but `api/candidates.py` breaches it via `repo._db` — #41).
- Frontend: React 19 + Tailwind v4 + Cytoscape; `NODE_ENV=test CI=1` for vitest.
- Visibility filter: `visible_from_order IS NOT NULL AND visible_from_order <= $visible_until_order` — NEVER fork a second implementation (directly relevant to #49).
- Test hygiene: shared live Neo4j — never delete real user rows; teardown only what tests created; scratch-series for candidate/retrieval tests (D-07).

### Integration Points
- FEAT-06/FEAT-01/FEAT-08 (search/palette/path): `backend/app/api/graph.py` new routes → existing tools; `frontend/src/hooks/useGraph.ts` payload.
- FEAT-09: new share-token repository + token-gated route wrapping the existing graph query path.
- REBRAND-01: rename sweeps package dirs, `pyproject.toml`, `docker-compose.yml`, `README.md`, `docs/DEPLOYMENT.md`, `/health` service field, UI title.
- #48: `retrieval/pipeline.py` `_accumulate`/`_finalize` + `assemble_context` notes bucket.
- #56: `useWatchProgress.ts` `requestChange` + `useEffect` hydration race + `App.tsx` graph key.

</code_context>

<specifics>
## Specific Ideas

- "all lets go fast" — user explicitly wants the full 57-finding scope with no
  deferral of #46–57; planning should batch aggressively (fewer, bigger plans).
- User picked: full fcose cluster layout (#57), scratch-series + teardown
  test isolation (#15), snapshot-at-creation share links (FEAT-09), Markdown-only
  export (FEAT-05), MIT license (PROB-10).

</specifics>

<deferred>
## Deferred Ideas

- God-file decomposition of the 5 big modules — explicitly deferred in
  REQUIREMENTS.md (maintainability only, not a safe-launch blocker); #57's
  GraphCanvas extraction is the exception and stays in scope (D-06).
- Versioned Neo4j schema migrations (#19) — deferred in REQUIREMENTS.md;
  seed-as-schema continues.
- Second demo series (FEATURE-IDEAS §7) — validates series-genericity; not in
  the 10 FEATs, defer.
- Turkish UI strings (FEATURE-IDEAS §7) — backend prompt language exists; UI
  chrome localization is not in FEAT-01..10/FEAT-11, defer.
- Multi-region/HA hosting, paid tier, mobile native apps — out of scope (REQUIREMENTS.md).

None — discussion stayed within phase scope beyond the above ledger items.

</deferred>

---

*Phase: 9-Feature Expansion & Full Audit Remediation*
*Context gathered: 2026-08-05*
