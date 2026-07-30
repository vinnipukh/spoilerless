---
last_mapped: 2026-07-30
focus: concerns
---

# Concerns

## Summary

Prototype v0 (Phases 1-4, plus backend-only Phase 5) has shipped and been archived. The app is now a working spoiler-safe graph UI (React + Cytoscape.js) backed by FastAPI + Neo4j, with notes/editing, revision history, and auth. The most relevant open item for planning is **Phase 05.1 (candidate review frontend UI)**: Phase 5 built a complete candidate/extraction review API with zero frontend consumption. This document leads with that gap, then covers general tech debt, workarounds, and risks found across `backend/` and `frontend/`.

## Phase 05.1 Planning Concern: Candidate Review Backend Has No Frontend

### API Surface Ready to Consume

`backend/app/api/candidates.py` (321 lines) exposes a full REST surface under `/api/series/{series_id}/candidates`:

- `POST /api/series/{series_id}/candidates` — `ingest_candidates`: bulk-ingest an `ExtractionBatchEnvelope` (see `backend/app/domain/extraction.py`) of claims as `origin="candidate"` / `status="candidate"` claims.
- `GET /api/series/{series_id}/candidates` — `list_candidates`: list candidate claims, optionally filtered by `visible_until_order` (spoiler boundary).
- `GET /api/series/{series_id}/candidates/{claim_id}` — `get_candidate`: fetch a single candidate claim with evidence/source details (`_read_claim_query()`, `backend/app/api/candidates.py:33`).
- `POST /api/series/{series_id}/candidates/{claim_id}/approve` — `approve_candidate`: promotes `origin: 'candidate'` → `status: 'canonical'`, writes a revision (`backend/app/api/candidates.py:173`).
- `POST /api/series/{series_id}/candidates/{claim_id}/reject` — `reject_candidate`: sets `status: 'rejected'`, writes a revision (`backend/app/api/candidates.py:225`).
- `PATCH /api/series/{series_id}/candidates/{claim_id}` — `edit_candidate`: edits mutable fields (`EditCandidateRequest`, `backend/app/api/candidates.py:55`), writes a before/after revision (`backend/app/api/candidates.py:275`).

Repository logic lives in `backend/app/graph/candidates.py` (263 lines, `CandidateRepository`). Both approve/reject/edit guard with `WHERE claim.origin = 'candidate'` and return `409 cannot_approve_non_candidate` if the claim isn't in candidate state — the review UI must handle this 409 for already-actioned claims (e.g. double-click / stale list).

Backend test coverage exists and passes: `backend/tests/test_candidate_ingest.py`, `backend/tests/test_candidate_review.py`. Use these as the source of truth for request/response shapes when building the frontend client.

### No Frontend Wiring Exists Yet — Build From Scratch

`frontend/src/api/` has one file per backend resource already consumed: `auth.ts`, `client.ts`, `graph.ts`, `revisions.ts`, `series.ts`, `userContent.ts`. **There is no `candidates.ts`.** No component under `frontend/src/components/` references the candidates endpoints. Phase 05.1 needs to add:
- `frontend/src/api/candidates.ts` (client following the pattern in `frontend/src/api/revisions.ts` or `userContent.ts`)
- A review UI (list, detail, approve/reject/edit actions) — no existing component to extend; this is net-new surface area, not a refactor.
- A data hook (`frontend/src/hooks/`) following the pattern of `frontend/src/hooks/useRevisions.test.tsx` (see also non-test `useRevisions` hook) if the review UI needs polling/refetch-after-action behavior.

### Origin-Based Visual Styling Exists But Only Handles `"canonical"` / `"user"` — Not `"candidate"`

Phase 03.1 established an origin-based visual convention that Phase 05.1 should reuse, not duplicate, but it is **incomplete for candidates today**:

- `frontend/src/components/graph/graphStylesheet.ts:42-47` — the base node style defaults `border-style: 'dashed'` for all origins, with a comment explicitly noting this is "the forward-compatible default border for non-canonical origins (user-content, **future candidate**/automatic data)". Only `node[origin = "canonical"]` (`graphStylesheet.ts:104`) is overridden to `solid`. There is no explicit `node[origin = "candidate"]` selector — candidate nodes currently fall through to the generic dashed default, visually indistinguishable from user-content nodes.
- `graphStylesheet.ts:184-187` already has a claim-level (not node-level) selector: `edge[claimStatus="candidate"]` → dashed line, separate from the node `origin` attribute. This suggests candidate *claims* render as edges with `claimStatus` data, which the future review UI's node/edge inspection should reuse rather than re-deriving.
- `frontend/src/components/detail/DetailPanel.tsx:548-556` only special-cases `selectedNode.origin === 'user'` to show a "User" badge; every other origin (including `'candidate'`, if it were ever surfaced as a node) falls into the plain-text fallback branch (`graphStylesheet.tsx:556`). No `"candidate"` badge/label exists yet — Phase 05.1 should decide whether candidate claims need their own DetailPanel treatment or stay purely in a dedicated review UI outside the graph canvas.
- `frontend/src/types/graph.ts:3` and `frontend/src/types/userContent.ts` type `origin` as a bare `string`, not a union — noted in-code as intentional ("wire value... is literally 'canonical'"). This means TypeScript will not catch a typo'd `"candidate"` origin value; the review UI's own types should define the candidate claim shape explicitly (matching `backend/app/domain/extraction.py` / `EditCandidateRequest`) rather than relying on the loose `origin: string` graph types.

**Net guidance for 05.1 planning:** the candidate review UI is most likely a separate screen/panel (a queue/list + detail + approve/reject/edit form) rather than something bolted onto `GraphCanvas`/`DetailPanel`, since candidates are pending claims not yet part of the canonical graph the canvas renders. If candidates should also appear *within* the graph canvas (e.g. as a toggleable "pending" layer), the dashed-border convention and `claimStatus="candidate"` edge selector are there to build on — but the `node[origin = "candidate"]` selector and DetailPanel badge branch still need to be added.

## Backend Concerns

### Degraded Startup Swallows Neo4j Connection Errors Silently

`backend/app/main.py:44-46` (`lifespan`) catches all exceptions from `database.verify_connection()` and continues startup, relying on `/health` to report `database: "unavailable"`. This is intentional per the inline comment, but any route that assumes a live connection (most of them — see below) will surface as a raw 500/driver exception rather than a clean degraded-mode response if Neo4j is down when a request comes in.

### Direct Database Access in Route/Repository Layers

Routes and repositories (`backend/app/api/series.py`, `backend/app/graph/candidates.py`, `backend/app/revisions.py`) open Neo4j sessions and run Cypher directly rather than going through a single abstraction. This is workable at current scale but means query construction, error translation, and transaction handling are duplicated per module — worth consolidating if more resource types are added beyond candidates/revisions/user-content.

### String-Built Cypher in `edit_candidate`

`backend/app/api/candidates.py:298` builds part of the Cypher query with an f-string (`MATCH (claim:Claim {{id: $claim_id, series_id: $series_id, origin: 'candidate'}})`) rather than pure parameterization for the SET clause (field names come from `EditCandidateRequest`'s known field set, not raw user input, so this is not directly exploitable today — but it's a pattern that becomes risky if new editable fields are added without equally strict validation).

### No Docker Compose / Documented Local Neo4j Setup

Still no `docker-compose.yml` or setup script in the repo root or `backend/`. New contributors must infer Neo4j startup from `.env.example` and `backend/app/core/config.py`. This was flagged in the prior mapping and remains true.

## Frontend Concerns

### React 19 `act()` Polyfill Workaround in Test Setup

`frontend/src/test/setup.ts:7-16` manually polyfills `React.act` because React 19 canary (19.2.x) doesn't export it and `react-dom/test-utils` expects it — without the polyfill, every test touching React throws `"React.act is not a function"`. This is a stopgap tied to a canary/pre-release React version; when the project moves to a stable React 19 release, re-check whether this polyfill is still needed (a stable release may export `act` natively, making the shim dead code that silently no-ops `act()` calls — which by itself is a risk: the polyfill's `(fn) => fn()` implementation doesn't actually flush React's act queue the way real `act()` does, so it could mask async-update warnings in tests).

### `console.log` Debug Statement Left in Test Setup

`frontend/src/test/setup.ts:37` (`console.log('[SETUP] before matchMedia polyfill, typeof:', typeof window.matchMedia)`) is a leftover debug log that runs on every test file load, adding noise to CI/test output. Safe to remove once confirmed it's not gating a known flaky-ordering issue.

### `DetailPanel.tsx` Is a 730-Line Single Component

`frontend/src/components/detail/DetailPanel.tsx` is by far the largest component in the frontend (730 lines vs. next-largest `GraphCanvas.tsx` at 355). It has accumulated node inspection, origin badges, notes/editing (Phase 3), and revision history entry points (Phase 4) in one file. Before Phase 05.1 adds candidate-review-specific rendering here (if any), consider whether new UI belongs in a separate component to avoid this file growing further.

### `origin` Typed as Loose `string`, Not a Union

`frontend/src/types/graph.ts:3` and `frontend/src/types/userContent.ts` both type `origin` as `string` with an inline comment explaining this is deliberate (the wire value is `'canonical'`, not a design-doc placeholder). The tradeoff: TypeScript cannot catch a mistyped origin value (e.g. `'canidate'`) anywhere it's compared with `===`. Acceptable as-is per the documented rationale, but any new origin value introduced by Phase 05.1 (e.g. surfacing `'candidate'` node origins) should be spot-checked manually since the type system won't help.

## Product/Data Concerns

### Seed Data Still Limited to 3 Episodes

`data/dexter/metadata/episodes.json` still covers only S01E01-03. Sufficient for prototype UAT but not for validating cross-season spoiler-boundary edge cases or larger graphs (performance, layout crowding, candidate-queue volume).

### Candidate Ingestion Has No Producer Yet

`ingest_candidates` (`backend/app/api/candidates.py:105`) accepts an `ExtractionBatchEnvelope` from "a future extractor," but no extractor/LLM pipeline exists in this repo yet — ingestion can currently only be exercised via tests or manual API calls. Phase 05.1's review UI will have nothing real to review until an ingestion source exists; seed/fixture candidate data (or a manual ingest script) will likely be needed to build and demo the review UI.

## Testing/Quality Concerns

- Backend has real test coverage now: `backend/tests/` includes `test_auth.py`, `test_candidate_ingest.py`, `test_candidate_review.py`, `test_extraction_models.py`, `test_frontend_contract_doc.py`, `test_graph_api.py`, `test_openapi_contract.py`, `test_revisions.py`, `test_revision_models.py`, `test_seed_idempotency.py`, `test_user_content_api.py`, `test_user_content_models.py`, `test_user_content_repository.py`. No `test_candidates_frontend_gap`-style contract test ties the OpenAPI candidates surface to frontend usage — `test_openapi_contract.py` and `test_frontend_contract_doc.py` are worth checking before 05.1 to see if they need updating once a frontend client is added.
- Frontend has real test coverage too: `App.test.tsx`, `GraphCanvas.test.tsx`, `DetailPanel.test.tsx`, `RevisionHistoryPanel.test.tsx`, `useRevisions.test.tsx`, plus fixtures in `frontend/src/test/fixtures/`. No test file yet references candidates (expected, since no candidate UI exists).
- No visible CI configuration (`.github/workflows/` not found) — confirm before relying on CI to catch regressions; verification currently appears to run in dev/plan-phase loops (per `.planning/`) rather than automated CI.
- No project root `README.md` with setup/verification instructions was found at time of mapping — confirm this is still true before onboarding new contributors.

## Security Notes

- `.env` remains gitignored; `.env.example` uses placeholders only — no secrets read or documented here.
- `backend/app/api/candidates.py:298`'s f-string-built Cypher (see above) is not attacker-controlled today but is worth tightening if the editable-field allowlist ever expands.
- Auth exists (`backend/app/api/auth.py`, `frontend/src/components/auth/`) — this mapping did not re-audit auth/session security in depth; treat as unverified for this pass since focus was `concerns` breadth, not a security review. Run `/security-review` separately if a security-focused audit is needed before shipping candidate-approval actions (which mutate canonical graph state) to production.
