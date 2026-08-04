# Phase 9: Feature Expansion & Full Audit Remediation — Research

**Researched:** 2026-08-05
**Domain:** Full-stack remediation (FastAPI + Neo4j + React/Cytoscape) + 11 features + product rename, zero-cost constraint
**Confidence:** HIGH (nearly every claim verified against live tree this session; see tags)

## User Constraints (from CONTEXT.md)

> Copied verbatim from `09-CONTEXT.md` — the planner MUST honor these. Locked decisions are research targets, not options.

### Locked Decisions

- **D-01:** Phase 9 targets every finding in `docs/PROBLEMS.md` (57 as of 2026-08-05), not just the 45 REQUIREMENTS.md was written against. The planning step MUST extend `.planning/REQUIREMENTS.md` with new PROB entries for #46–57 before/when writing plans (mapping: #46→PROB-22, #47→PROB-23, #48→PROB-24, #49→PROB-25, #50→PROB-26, #51→PROB-27, #52→PROB-28, #53→PROB-29, #55→PROB-30, #56→PROB-31, #57→PROB-32; #54 is context-only, no code).
- **D-02:** `docs/PROBLEMS.md` is the canonical problem ledger; planning must read it in full and cite finding numbers per plan, never plan from REQUIREMENTS.md alone.
- **D-03:** Graph canvas density (#57) — user chose **full cluster-aware layout**: replace the flat `cose-bilkent` pass with **cytoscape-fcose** (new dependency) using compound/cluster parent nodes driven by stable data keys (subplot/cluster tag or `Event.sequence_in_episode` bands).
- **D-04:** Also ship: node-type/edge-type filter toggles (FEAT-11), zoom-based label culling, focus/neighborhood mode (reuse existing `faded`/`selected-dominant` classes via a focus reducer), deterministic layout (seed positions or cache per boundary), edge bundling or opacity falloff.
- **D-05:** Update `GraphCanvas.test.tsx:200`'s `toHaveLength(11)` to the enriched S01E01 counts or make it count-independent.
- **D-06:** Prefer extracting (layout config, filter state, focus reducer) over piling into `GraphCanvas.tsx`; god-file decomposition itself stays out of scope.
- **D-07:** Test isolation — user chose **scratch-series + teardown fixtures** over Testcontainers. Candidate/seed tests move to scratch `series_*` ids with teardown fixtures; one-time zombie sweep of 3,855 `:AppUser` + 21 expired `:Session` nodes (never delete real dev user `ae8a41b7-db96-40e8-b6c2-2e3c69aedb11`); CI gains a DB-pollution gate (PROB-06 / #14 / #15 / #46).
- **D-08:** Tests must never mutate the real `series_dexter` graph or real user rows; seed-idempotency assertions become order/state-independent where the ledger calls for it.
- **D-09:** FEAT-09 share links — **snapshot-at-creation**: token stores `series_id` + boundary + `created_at`; read-only route reuses the SAME spoiler-filtering path as `api/graph.py` (never a second, looser code path). A link always shows exactly what was visible at creation.
- **D-10 (stated discretion):** tokens revocable (delete = revoke), default 30-day expiry, random URL-safe token via stdlib `secrets`; new Neo4j label for share tokens; unauthenticated-but-token-gated route; frontend read-only route distinct from the authenticated shell.
- **D-11:** FEAT-05 export — **Markdown only** (zero new deps). Backend renders visible knowledge (notes, claims, evidence) as Markdown; FE downloads a `.md` file. No jspdf/PDF.
- **D-12:** REBRAND-01 — rename every user-visible and repo-level `hdgrafcehennemi` reference → `spoilerless`: package dirs, pyproject, docker-compose container name, service names, README, DEPLOYMENT.md, `/health` `service` field, UI title. Git history intentionally untouched; runtime/deploy names updated. **Sequencing note: do the rename EARLY in the phase** so later feature plans touch renamed paths.
- **D-13:** 09-01 (UptimeRobot) is DONE — verified live, UAT #11 pass. No plan needed.
- **D-14:** Remaining carry-overs IN scope as plans: 09-02 (CI smoke fixes → main, confirm Actions green), 09-03 (admin-role live verification with `ADMIN_EMAILS` configured), 09-04 (`REDIS_URL` on Render + live 429/cache verification), 09-05 (seed-test pollution — folded into D-01/#46/PROB-22), 09-06 (frontend lint 0-error — folded into PROB-08), 09-07 (full CI/CD: dependency scanning, artifact publication, staged promotion, branch protection), 09-08 (full observability: centralized logs, metrics dashboards, incident runbook).
- **MIT license** for PROB-10/#28 (user choice, per 09-DISCUSSION-LOG).

### Claude's Discretion
- Exact fcose layout tuning, compound-node cluster tags, focus-reducer shape.
- Share-token label name, exact expiry sweep mechanism.
- FEAT-04 series dashboard: augment the existing dropdown (keep dropdown, add dashboard as entry point) unless evidence says replace.
- FEAT-02 timeline placement: tabbed approach consistent with existing panel layout.
- Which remaining #46–57 items land in which plan wave.
- Exact `ALLOWED_EMAILS` value for 09-03 (operator supplies).

### Deferred Ideas (OUT OF SCOPE — do not plan)
- God-file decomposition of the 5 big modules (only #57's GraphCanvas extraction stays in scope).
- Versioned Neo4j schema migrations (#19) — seed-as-schema continues.
- Second demo series; Turkish UI strings; multi-region/HA, paid tier, mobile native apps.
- POLISH-01..03 belong to Phase 10, NOT here.

## Project Constraints (from HERMES.md)

No `HERMES.md` exists in the repo (verified: `.hermes/` contains only `desktop-attachments/`; `.planning/config.json` `claude_md_path` points at `./.hermes/HERMES.md` which is absent). No HERMES.md directives to enforce. The governing constraints are `docs/PROJECT-SPEC.md` §3 (non-negotiable invariants), §6 (visual language), §7 (GraphRAG constraints) — summarized in §Architecture Patterns below — plus the zero-cost constraint and the operator-touch-last sequencing requirement.

## Summary

Phase 9 is three programs of work bolted onto a live, already-deployed v1.3 app: (1) remediate all **57** findings in `docs/PROBLEMS.md` (32 PROB requirements, clustered into five subsystems — auth/ownership, tests+isolation, chat/LLM, docs/hygiene, graph canvas), (2) ship **11 features** (FEAT-01..10 + FEAT-11 second-brain touches), and (3) **REBRAND-01** `hdgrafcehennemi` → `spoilerless` — all under a hard zero-cost constraint with verification via the free local stack (`FakeLLMProvider`, scratch-series live-DB tests in CI's fresh Neo4j container, vitest) and with the three operator-touch carry-overs (09-02 CI-green confirm, 09-03 admin live check, 09-04 REDIS_URL) sequenced LAST.

**Verified this session (high-confidence anchors):** the `#42` Google-verifier `NameError` is already fixed in the live tree (the `from google.auth.transport import requests` at `auth.py:62` binds `google` in function scope, so the `except google.auth.exceptions.TransportError` at line 73 can no longer NameError) — what remains for PROB-14/23 is the **behavioral regression test**, not the fix. `backend/.env` and `frontend/.env.local` no longer exist (PROB-30's file-merge is largely done; `envDir: '..'` in `vite.config.ts` + the GOOGLE_CLIENT_ID equality check remain). The `ci-smoke-test` branch no longer exists locally or on the remote (`git ls-remote` shows only `main`), and the eslint config with the 3 React-Compiler-era rules scoped to `warn` is already in local `main` — so 09-02 is primarily "push local main (4 commits ahead of `origin/main` @ `288743e`) and confirm GitHub Actions green," plus closing out whatever lint *errors* remain (PROB-08/09-06 must FIX the stale-ref bugs, not just scope rules). `cytoscape-fcose@2.2.0` passes the package-legitimacy gate (OK, 11.3M weekly downloads, same iVis-at-Bilkent authors as cose-bilkent); `fuse.js@7.5.0` is flagged SUS (too-new signal) — recommend zero-dep substring search for FEAT-01/07/08, with fuse.js only behind a `checkpoint:human-verify`.

**Primary recommendation:** Sequence as (0) rename sweep + git-state push, (1) backend correctness clusters with scratch-scoped tests, (2) test isolation/infra hardening, (3) frontend features (PROB-31 progress-hook fix BEFORE FEAT-03/advance UX; PROB-32 graph canvas LAST in the feature wave), (4) docs alignment, (5) FINAL operator-touch wave (09-02 → 09-03 → 09-04 + optional live reseed). Batch aggressively (config `granularity: coarse` matches the user's "all lets go fast"); every plan cites PROBLEMS.md finding numbers; every live-AuraDB mutation (zombie sweep, reseed) is either a read-only scripted audit or an explicit checkpoint-gated step, never a bare test run.

## Phase Requirements

In scope (from `.planning/REQUIREMENTS.md` + ROADMAP §Phase 9 + 09-CONTEXT):

| Group | Requirements | Resolves |
|---|---|---|
| Auth & ownership | PROB-01, 02, 03, 04, 05, 09, 12, 14, 15, 16, 25, 26, 27 | #1–4, #9, #11, #12, #13, #20, #32–34, #37, #42, #43, #49–51 |
| Tests & isolation | PROB-06, 07, 08, 18, 22, 23 (+09-05, 09-06) | #14–17, #40, #46, #47 |
| Chat / LLM | PROB-13, 24, 28 | #35, #48, #52 |
| Docs & hygiene | PROB-10, 11, 19, 20, 21, 29, 30 + DOCS-04 | #21–26, #28, #29, #41, #44, #45, #53, #55 |
| Graph canvas | PROB-32 (feeds FEAT-11) | #57 |
| Features | FEAT-01..10, FEAT-11 | ROADMAP SC#5, SC#6 |
| Rebrand | REBRAND-01 | ROADMAP SC#0 |
| Carry-overs | 09-02..09-08 (09-01 done) | OPS-01, AUTH-03, SEC-03, INFRA-02, PROB-06/08 |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Ownership/actor binding (PROB-01/02/26) | `repository/user_content.py` + `api/*.py` deps | `domain/user_content.py` DTOs | Route deps gate, repos bind, DTOs expose `user_id`/`created_by` |
| Spoiler boundary derivation (PROB-25) | `repository/user_content.py` + `repository/change_set.py` | new shared helper in `spoiler/` or `services/` | One rule: `max(episode order, current progress)` fail-closed, no forked filters |
| Session hygiene (PROB-03) | `repository/session.py` + `services/auth.py` | new background sweep | uuid4 ids + sweep job (lazy + periodic) |
| Test isolation (PROB-06/22) | `backend/tests/` fixtures | CI `ci.yml` | scratch-series fixture pattern already proven in `test_retrieval_tools.py` |
| Chat failure handling (PROB-13) | `services/chat.py` + `api/chat.py` | `domain/chat.py` status field | persist-with-status + log-before-generic-event |
| Notes→context bridge (PROB-24) | `retrieval/pipeline.py` | `spoiler/filter.py` read path | accumulator bucket + `assemble_context(notes=...)` |
| Graph canvas (PROB-32/FEAT-11) | `frontend/src/components/graph/` (extracted modules) | new `GraphFilterPanel.tsx`, focus reducer | fcose layout + filter state + focus reducer, not a bigger god-file |
| Share links (FEAT-09) | new `backend/app/api/share.py` + repo | `spoiler/filter.py` (reused, never forked) | Token-gated route wrapping the SAME graph path |
| Feature search/palette (FEAT-01/07/08) | `frontend/src/lib/` + new component | existing `useGraph.ts` payload | Client-side over already-filtered payload — no new spoiler surface |
| Rebrand (REBRAND-01) | repo-wide sweep | docs + tests | Mechanical grep-replace gated by full CI suite |

## Standard Stack

### Core (all already installed — zero new backend deps)

| Library | Version | Purpose | Why Standard |
|---|---|---|---|
| FastAPI + Pydantic v2 strict | 0.140.7 / 2.13.4 | All new routes (share, export, path) | Existing stack; FEATURE-RESEARCH confirms zero new backend deps for every feature [VERIFIED: `frontend/package.json`, `pyproject.toml`] |
| neo4j async driver | 6.2.0 | New `ShareToken` label, scratch-series queries, sweeps | Existing; AuraDB TLS normalization already in `graph/database.py` |
| stdlib `secrets` | — | Share tokens (FEAT-09), collision-proof ids | D-10: `secrets.token_urlsafe(32)` — never uuid for tokens [VERIFIED: Python stdlib] |
| Cytoscape.js + cose-bilkent | 3.34.0 / 4.1.0 | Existing canvas | Keep; fcose replaces the layout pass only |
| **cytoscape-fcose** (NEW) | **2.2.0** | Cluster-aware compound layout (D-03/#57) | Same Bilkent family as cose-bilkent; `relativePlacement` constraints; `cose-base ^2.2.0` already a transitive dep [VERIFIED: npm registry + legitimacy gate OK] |
| React 19 + Tailwind v4 + radix/shadcn | existing | All frontend features | Existing stack |

**Installation (the ONLY new dependency in the phase):**
```bash
cd frontend && npm install cytoscape-fcose@2.2.0
```

**Version verification (this session):** `cytoscape-fcose@2.2.0` (published 2023-01-17, 11.3M weekly downloads, repo `iVis-at-Bilkent/cytoscape.js-fcose`, no postinstall, deprecated:false — checked via `npm view` + `gsd-tools query package-legitimacy`). `fuse.js@7.5.0` (12.6M weekly downloads, `krisk/Fuse`) but **SUS "too-new"** per the seam — see audit below.

### Supporting (optional, NOT required)

| Library | Version | Purpose | When to Use |
|---|---|---|---|
| `fuse.js` | 7.5.0 | Fuzzy search (FEAT-01/07/08) | ONLY if substring search feels too strict — gate behind `checkpoint:human-verify` (SUS) |
| Playwright/Cypress | — | Browser E2E | NOT in this phase — no E2E framework is configured; jsdom + live-DB tests are the established pattern |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|---|---|---|
| cytoscape-fcose (D-03) | cytoscape-cola with grouping | cola is slower/less maintained; fcose is the ecosystem-standard compound layout; user locked fcose |
| Scratch-series + teardown (D-07) | Testcontainers | User rejected Testcontainers (heavy on Windows, doesn't test real AuraDB, CI already has a service container) |
| Markdown export (D-11) | jspdf PDF | jspdf = new dep + heavier; user locked Markdown-only |
| Substring search (FEAT-01/07/08) | fuse.js | fuse.js is SUS-flagged; substring against already-fetched nodes is fine at this scale (FEATURE-RESEARCH) |

## Package Legitimacy Audit

> Run via `gsd-tools query package-legitimacy check --ecosystem npm` this session.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---|---|---|---|---|---|---|
| cytoscape-fcose | npm | ~3.5 yrs (2023-01-17) | 11.3M/wk | github.com/iVis-at-Bilkent/cytoscape.js-fcose | OK | **Approved** — the only new dependency |
| fuse.js | npm | metadata "too-new" signal | 12.6M/wk | github.com/krisk/Fuse | SUS | **Flagged** — if used, planner adds `checkpoint:human-verify` before install; recommendation is zero-dep substring search instead |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** `fuse.js` — the "too-new" signal conflicts with its 12.6M/wk downloads and long history (likely a metadata artifact), but per protocol it stays SUS: tag inline and gate any install behind `checkpoint:human-verify`. Primary recommendation remains: do not install it (substring search over the already-filtered graph payload is sufficient per `docs/FEATURE-RESEARCH.md` §1).
*No Python packages are added anywhere in this phase [VERIFIED: FEATURE-RESEARCH cross-cutting note — every backend-touching idea reuses FastAPI/Pydantic/neo4j/httpx].*

## Architecture Patterns

### System Architecture Diagram

```text
                         ┌────────────────────────────┐
                         │  React SPA (Vercel Hobby)  │
                         │ app.spoilerless.net        │
                         │ GraphCanvas (fcose) ·      │
                         │ search/palette · timeline  │
                         │ dashboard · export · share │
                         └─────────────┬──────────────┘
                                       │ X-LLM-* BYOK headers (localStorage)
                                       │ session cookie (SameSite=Lax, Secure)
                       ┌───────────────▼────────────────┐
                       │  FastAPI backend (Render free)  │
                       │  api.spoilerless.net            │
                       │  auth/ownership deps (PROB-01)  │
                       │  share-token route ──┐          │
                       │  export route        │          │
                       │  path route (FEAT-06)│          │
                       └───┬────────────┬─────┼──────────┘
                           │            │     │ (SAME filter path — D-09)
              ┌────────────▼───┐  ┌─────▼──────▼─────┐   ┌──────────────┐
              │ Neo4j AuraDB   │  │ spoiler/filter.py │   │ Upstash Redis│
              │ Free           │  │ (single boundary  │   │ (rate limit  │
              │ (graph + share │  │  derivation —     │   │  + graph     │
              │  tokens +      │  │  PROB-25/29)      │   │  cache)      │
              │  sessions)     │  └───────────────────┘   └──────────────┘
              └────────────────┘
   Tests: pytest → CI fresh Neo4j service container (never AuraDB)
          vitest → jsdom (FakeLLMProvider never hits network)
```

### Pattern 1: Scratch-series + teardown fixture (D-07, PROB-06/22)

**What:** Every candidate/seed/repository test that writes runs on a scratch `series_scratch_*` id and deletes everything it created in a teardown, matching the proven retrieval-test pattern.
**When to use:** All new/refactored backend tests that touch the graph.
**Example (existing, `backend/tests/test_retrieval_tools.py:74-75` [VERIFIED]):**
```python
SCRATCH_SERIES = "series_scratch_retrieval"

@asynccontextmanager
async def scratch_series(database: Neo4jDatabase) -> AsyncIterator[str]:
    """Yield the scratch series id, deleting everything created there after."""
    try:
        yield SCRATCH_SERIES
    finally:
        await database.execute_query(
            "MATCH (n {series_id: $sid}) DETACH DELETE n", sid=SCRATCH_SERIES
        )
```
**Teardown must also delete `UserSeriesProgress` rows and `origin='candidate'` nodes** — progress rows carry `series_id` but no `visible_from_order` and trip the seed-integrity audit; candidate residue is exactly the #14 root cause (`{'relationships': 33} != 27`). Cleanup pattern from the 08 CI runbook [VERIFIED: skill ref `08-ci-test-drift.md`]:
```python
await live_database.execute_query("MATCH (n) WHERE n.origin = 'candidate' DETACH DELETE n")
```

### Pattern 2: Zero-cost chat/LLM verification via `FakeLLMProvider`

**What:** `FakeLLMProvider` lives in PRODUCTION source (`backend/app/llm/provider.py:415`) — deterministic scripted `LLMEvent`s, records every call, never touches the network [VERIFIED: read this session]. All chat/pipeline/ChangeSet tests use it; the pipeline's citation validation reads the FINAL provider call's `done` event; scripts mixing tool-calls + cited `done` need a per-call-index provider (`index = len(self.calls)`).
**When to use:** Every chat/pipeline test. No test in this phase may spend LLM API money — the zero-cost constraint makes this the ONLY acceptable chat verification vehicle, plus `httpx.MockTransport` for the `ProductionGoogleVerifier` behavioral test (PROB-23) and dependency-override fakes (`FakeUserRepo`, `InMemorySessionRepository`) for route tests [VERIFIED: `backend/tests/test_settings_api.py`, `test_chat_api.py` patterns].
**Config pitfall:** `get_settings()` is `lru_cache`d — `monkeypatch.setattr(get_settings(), "llm_max_tool_rounds", 3)`, never replace the instance [VERIFIED: skill].

### Pattern 3: Expose an allowlisted retrieval tool through a direct route (FEAT-06)

**What:** `find_path` (and `get_character_context`) already exist as bounded, allowlisted, boundary-injected tools in `backend/app/retrieval/tools.py`. FEAT-06 = a thin route that calls the same executor with the boundary already resolved from `api/deps.py` — no new retrieval logic, no new spoiler surface (FEATURE-RESEARCH's repeated pattern) [VERIFIED: FEATURE-RESEARCH §1].
**When to use:** FEAT-06 only; keeps PROJECT-SPEC §7 GraphRAG constraints intact (still allowlisted, still boundary-filtered, server-injected params).

### Pattern 4: fcose cluster-aware layout (D-03/D-04, PROB-32)

**What:** Register fcose (`cytoscape.use(fcose)`), drive `layout: {name: 'fcose', ...}` with compound parent nodes per cluster key. `layoutOptionsFor` currently handles only `'cose-bilkent' | 'cose'` (`GraphCanvas.tsx:49-60` [VERIFIED]) — extend the union with `'fcose'`. Cluster keys: subplot/cluster tag or `Event.sequence_in_episode` bands (data already carried) [VERIFIED: #57 root-cause text + D-03].
**Pitfalls:** react-cytoscapejs's declarative layout prop never re-lays-out on element change — the code already calls layout imperatively from an effect keyed on `graph` (comment at `GraphCanvas.tsx:~63` [VERIFIED]); the fcose swap must ride the same imperative path. Compound nodes need a `parent` field on child node data; register once at module level with a try/catch fallback (existing cose-bilkent pattern, lines ~37-44). The test double's fake `cy` has no real `.layout()` — keep the existing guard.
**Also ship (D-04):** node/edge-type filter toggles (Cytoscape `display`/class toggling — new `GraphFilterPanel.tsx`), zoom-based label culling, focus reducer over existing `faded`/`selected-dominant` classes, deterministic positions (cache per boundary or seeded), edge opacity falloff. **Extract** `layoutConfig.ts`, `filterState.ts`, `focusReducer.ts` per D-06 instead of growing the 530-line god-file [VERIFIED: #18/#53/#57].

### Pattern 5: Share-token snapshot route (FEAT-09, D-09/D-10)

**What:** New `ShareToken` Neo4j label storing `token_hash` (store hash, not raw token), `series_id`, `visible_until_order`, `created_at`, `expires_at`, `revoked_at`. Route `GET /api/share/{token}/graph` resolves the token (hash lookup), checks expiry/revocation, then calls the SAME graph assembly path used by `api/graph.py` with `user_id=None` + the stored boundary — one filter implementation, per D-09. Token = `secrets.token_urlsafe(32)` [VERIFIED: stdlib]. Expiry sweep reuses the session-sweep mechanism (PROB-03). Frontend: read-only route outside `AppShell` (React Router path like `/share/:token`), no login wall, no write controls.

### Pattern 6: REBRAND-01 rename sweep (D-12, SC#0) — EARLY

**What:** Full mechanical rename `hdgrafcehennemi` → `spoilerless` across the verified surface (see Runtime State Inventory + the tracked-file list below). Do it as the FIRST plan (wave 0) so every later feature plan lands on renamed paths (D-12's own sequencing note).
**Verified rename surface (tracked files containing `hdgrafcehennemi`, this session):** `pyproject.toml` (project name + `hdgraf-setup` console script), `docker-compose.yml` (container name), `render.yaml` (service `name: hdgrafcehennemi-api`), `backend/requirements.txt` (generated uv-export artifact — regenerate or delete per #30), `backend/scripts/smoke.sh`, `backend/app/main.py` (`SERVICE_NAME = "hdgrafcehennemi-backend"` — /health `service` field), `backend/tests/test_graph_api.py:101` (**asserts the service field — rename breaks this test; update it**), `index.html` (root landing page: `<title>HD Graf Cehennemi</title>` at `frontend/index.html:12` + root `index.html` `window-title`/`GITHUB_REPOSITORY_URL`), `README.md`, `docs/*` (API, ARCHITECTURE, DEVELOPMENT, CONFIGURATION, GETTING-STARTED, DEPLOYMENT, ROADMAP, PROJECT-SPEC, PROBLEMS), plus `frontend/src/lib/byok.ts:9` (`BYOK_STORAGE_KEY = 'hdgraf:byok-llm-settings'` — localStorage key; rename or read-compat migrate) and UI strings "HD Graf Cehennemi" in frontend components.
**Import-root question (decision needed — see Open Questions):** "package dirs" literally includes the `backend/` import root (`backend.app.*` imports, `uv run --project backend`, `uvicorn backend.app.main:app`, conftest `sys.path`, CI `uv run --project backend python -m backend.app.graph.setup`, render `startCommand`). A full `backend/` → `spoilerless/` rename is mechanical (`git grep -l 'backend.app' | xargs sed`-class, ~dozens of files) but touches every test import; the full CI suite (fresh-container backend job) is the safety net. Recommendation: do the FULL rename including the import root in the dedicated wave-0 plan, and verify with the complete CI suite + `npm run build`; if the planner wants to de-risk, the metadata-only subset (pyproject/scripts/docker/render names, UI/docs/health field, localStorage key) still satisfies every user-visible reading of D-12 — flag as a plan-check decision.

### Anti-Patterns to Avoid
- **[Second visibility filter]:** FEAT-09's share route MUST call the existing filter path — a second, looser copy is the exact class of bug #49/#53 flag and a spoiler leak (D-09 is explicit).
- **[Mocking the API client in wire-shape tests]:** the #43 progress-422 and 08-01 chat-422 bugs both shipped because FE tests mocked the client and asserted the buggy payload (PROB-23/#47). Wire-shape tests assert the REQUEST BODY via a transport-level `fetch` stub (pattern: `frontend/src/api/chat.test.ts` replaces `globalThis.fetch`), never `vi.mock('@/api/progress')`.
- **[Fixing lint by scoping more rules to warn]:** the 3 React-Compiler-era rules are already scoped to warnings (eslint.config.js:28-39 [VERIFIED]) — PROB-08/09-06 must FIX the stale-ref bugs (move `fetchKeyRef.current` writes out of render bodies into effects), not add more exemptions.
- **[Running the full suite against AuraDB]:** AuraDB Free flood-blocks after heavy request traffic (~15-min cooldown, 08-04 UAT incident [VERIFIED: skill]). CI's fresh Neo4j service container is the ONLY full-suite target; live AuraDB is for read-only audits + operator UAT.
- **[Piling into GraphCanvas.tsx]:** D-06 mandates extracting layout config/filter state/focus reducer; the canvas is already 530 lines (#18/#53/#57).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Cluster-aware graph layout (#57) | Hand-placed coordinates / custom force sim | `cytoscape-fcose` (compound nodes + constraints) | Same family as cose-bilkent; battle-tested; user locked it (D-03) |
| Share tokens (FEAT-09) | Custom token math | `secrets.token_urlsafe(32)` | Cryptographically random URL-safe, stdlib, zero deps (D-10) |
| Fuzzy search (FEAT-01/07/08) | A scoring engine | Substring match over the fetched payload (fuse.js only behind checkpoint) | Data scale is small; FEATURE-RESEARCH says substring is fine |
| Markdown export (FEAT-05) | A Markdown library | Backend template/f-string over the SAME filtered read path | Zero deps (D-11); content is structured already |
| Rate limiting | New limiter | Existing `pyrate-limiter` Redis bucket infra (08-05) | Already multi-worker-safe; tests no-op `RateLimiter.__call__` via conftest |
| Session/share expiry sweep | Per-request slide logic | Background sweep job (lazy + periodic) | #9 root cause is slide-on-read; sweep once |
| Error-code casing (#20) | Per-route ad-hoc codes | One `error_codes` registry + contract test | One source of truth; see Open Questions |
| PDF export | jspdf | NOT in scope — Markdown only (D-11) | User locked; zero new deps |

**Key insight:** every new capability in this phase reuses an existing seam (allowlisted tools, `spoiler/filter.py`, `byok.ts` localStorage shape, `pyrate-limiter`, `RevisionRepository`) — the phase's risk is in *bridging* seams (notes→context #48, ownership on direct API #50, one visibility rule #49), not in new infrastructure. FEATURE-RESEARCH's cross-cutting note is verified: **zero new backend dependencies anywhere**.

## Runtime State Inventory

> Required for rename/refactor phases (REBRAND-01). All items verified this session unless tagged.

| Category | Items Found | Action Required |
|---|---|---|
| Stored data | Neo4j: no `hdgrafcehennemi` string in graph data (series ids are `series_dexter`-style); 3,855 zombie `:AppUser`, 21/21 expired `:Session` (5 orphaned), 1 progress row, 2 chat sessions (per #46 read-only audit) | Zombie sweep (PROB-22/D-07): delete test-created users/sessions only — NEVER `ae8a41b7-db96-40e8-b6c2-2e3c69aedb11`; no data-value rename needed |
| Stored data (browser) | `localStorage` key `hdgraf:byok-llm-settings` (`frontend/src/lib/byok.ts:9`) | Rename to `spoilerless:byok-llm-settings`; add read-compat migration (read old key once) or accept settings loss — small, pick in plan |
| Live service config | Render service `hdgrafcehennemi-api` (render.yaml + live dashboard); Vercel project; GitHub repo `vinnipukh/hdgrafcehennemi` (remote VERIFIED reachable via `git ls-remote`); UptimeRobot monitor; Cloudflare DNS `app.`/`api.` subdomains | Code: render.yaml/docker-compose/health names. **Operator:** GitHub repo rename + `git remote set-url`, Render service rename (render.yaml `name:` change creates a NEW service per blueprint semantics — operator dashboard action [ASSUMED]), UptimeRobot monitor rename. Sequence in the FINAL operator wave |
| OS-registered state | None found (no scheduled tasks/cron referencing the name) — verify once at plan time | None expected |
| Secrets/env vars | No env var names contain the product name (NEO4J_*, GOOGLE_CLIENT_ID, SESSION_*, FRONTEND_ORIGINS, REDIS_URL); `backend/.env` ALREADY DELETED [VERIFIED]; root `.env` may still carry dead `AUTH_DEV_CODE` (#55 fact-check: stale leftover) | PROB-30: `envDir: '..'` in `vite.config.ts` (VERIFIED missing), delete `backend/.env` (done), startup/CI equality check GOOGLE_CLIENT_ID vs VITE_GOOGLE_CLIENT_ID; remove dead `AUTH_DEV_CODE` line (operator-touch, .env is gitignored) |
| Build artifacts | `frontend/dist/`, `.venv`, `backend/requirements.txt` (generated uv export dup of uv.lock — #30), root `index.html` (static landing page), `frontend/README.md` (Vite boilerplate — PROB-10) | PROB-10 removes junk; `requirements.txt` regenerated or removed during rename; `hdgraf-setup` console entry renamed → reinstall (`uv sync`); CI cache keys unaffected |

**Nothing found in category:** OS-registered state (none — confirm with one `git ls-files`/tasklist sweep at plan time).

## Common Pitfalls

### Pitfall 1: AuraDB flood-blocking + suspension mask test failures
**What goes wrong:** Heavy live-DB request traffic makes AuraDB return `AuthError`/`Unauthorized` for a CORRECT password (08-04 UAT: "auradb blocked us because claude sent too many requests"); Free tier also suspends after inactivity. **Why:** platform rate policy, not a code bug. **How to avoid:** never point the full suite at AuraDB — CI fresh container or local docker (`scripts/env-local.sh`) only; live-DB mutations (zombie sweep, reseed) are one-shot scripted ops with explicit approval, run once, not in a loop. **Warning signs:** sudden `Unauthorized` on unchanged credentials mid-run.
[VERIFIED: skill ref `08-ci-test-drift.md` §6]

### Pitfall 2: Seed-count assertions stale the moment the seed grows
**What goes wrong:** Enriched S01E01 seed (32 Characters/39 Events/17 Objects/5 Orgs/22 Locations/132 Claims → ~90 visible nodes at boundary 1, #57) plus any new constraint/label (share-token constraint!) breaks exact-set seed tests (`test_seed_idempotency` asserts an exact constraint-label set — #19; adding the ShareToken constraint WILL break it [VERIFIED: #19 text + PROB-20]). **How to avoid:** PROB-06/22 makes seed assertions order/state-independent or fixture-derived; the constraint-set assertion must be updated when the ShareToken constraint lands — sequence the share-token plan to note it, or make the assertion additive (superset check). **Warning signs:** `{'relationships': 33} != 27` class failures in CI only.
[VERIFIED: #14, #19, #46, 08-ci-test-drift]

### Pitfall 3: The `$query` parameter collision and `:User` label trap
**What goes wrong:** `execute_query(query, **parameters)` collides with a bound param named `query` (TypeError); `(:User)` silently matches zero rows (schema uses `:AppUser`). **How to avoid:** name params `$entity_id`, `$search_term`, etc.; check labels against `repository/user.py`'s `MERGE (u:AppUser ...)` precedent. Any new Cypher (share tokens, sweeps, scratch teardown) follows both rules.
[VERIFIED: skill]

### Pitfall 4: FE wire-shape tests that mock the API client enshrine contract bugs
**What goes wrong:** #43 (progress 422) and the 08-01 chat 422 both shipped green because FE tests `vi.mock`'d the client and asserted the buggy payload. **How to avoid:** PROB-23 mandates wire-shape contract tests at the `fetch` transport level (chat.test.ts pattern); PROB-15's regression covers the exact three payload shapes (`{watched_through_order, view_as_of_order}` / `{view_as_of_order}` alone / `{visible_until_order}` alone).
[VERIFIED: #43, #47, skill chat-422 reference]

### Pitfall 5: `npm run build` (`tsc -b`) is the canonical typecheck, not bare `tsc --noEmit`
**What goes wrong:** plain `tsc --noEmit` on the solution tsconfig SKIPS referenced projects → test-file type errors pass locally and red the Vercel deploy (observed: `TS18048 'options' is possibly 'undefined'` in chat.test.ts, 5 sites). **How to avoid:** every frontend plan's verification includes `npm run build`; fix pattern `options?.headers`.
[VERIFIED: skill ref `08-01-deploy-build-traps.md`]

### Pitfall 6: Executor 429/503 deaths mid-plan (4× in Phase 8)
**What goes wrong:** subagents die on provider rate-limit/capacity errors; RED commits land, GREEN is uncommitted; self-reported status lies. **How to avoid:** recovery flow is disk-first per runbook (`git log --oneline -5` + `git status --short` + check SUMMARY exists → commit partial → re-dispatch REMAINING tasks with a minimal-call budget). Verify every executor return against git log/disk.
[VERIFIED: skill]

### Pitfall 7: `search_files` fails on this MSYS host; grep flags every line as non-ASCII
**What goes wrong:** search_files path-not-found on both path forms; `grep -En '[^\x00-\x7F]'` matches everything under MSYS. **How to avoid:** use `rg` via terminal for content search; `rg -n '[^\x00-\x7F]'` for the no-non-ASCII check.
[VERIFIED: skill]

### Pitfall 8: Rename sweep blind spots
**What goes wrong:** the rename misses test assertions (`test_graph_api.py:101` service field — WILL break), conftest `sys.path` (`backend/` insert), `uv run --project backend` in every runbook command + CI + render `startCommand`, `hdgraf-setup` console entry + `hdgraf:byok-llm-settings` localStorage key, root `index.html` `GITHUB_REPOSITORY_URL`, `.planning/` docs (keep old name in history; update references to the new repo URL). **How to avoid:** wave-0 rename plan carries the full inventory table above; verification = `git grep -il 'hdgrafcehennemi\|HD Graf Cehennemi'` returns ZERO hits in tracked product/docs files (except `.planning/` history + PROBLEMS.md audit trail, which intentionally keeps the old name).

## Code Examples

### FCose registration + compound layout (D-03)
```ts
// frontend/src/components/graph/layoutConfig.ts (NEW — extracted per D-06)
import fcose from 'cytoscape-fcose'
import cytoscape from 'cytoscape'
// register once, with the existing try/catch fallback pattern (GraphCanvas.tsx:37-44)
try {
  cytoscape.use(fcose)
} catch { /* fall back to 'cose' like the cose-bilkent guard */ }

export function layoutOptionsFor(name: 'fcose' | 'cose-bilkent' | 'cose') {
  if (name === 'fcose') {
    return {
      name: 'fcose',
      quality: 'default',          // 'default' | 'better'
      randomize: false,            // deterministic (D-04)
      nodeRepulsion: 8000,
      idealEdgeLength: 100,
      padding: 48,
      animate: prefersReducedMotion ? false : ('end' as const),
      // compound parents per cluster key drive visual separation
    }
  }
  /* existing cose-bilkent / cose branches unchanged */
}
// node data gains: parent: clusterId  (subplot tag or sequence_in_episode band)
```
*(Pattern per Cytoscape.js fcose docs — `[CITED: js.cytoscape.org/#layouts/fcose]`; exact option tuning is Claude's discretion per CONTEXT.)*

### Share token creation/read (FEAT-09, D-10)
```python
# backend/app/domain/share.py (NEW)
class ShareTokenCreate:  # internal, not a public API model
    series_id: str
    visible_until_order: int

# repository: store sha256(token) + series_id + boundary + created_at + expires_at
token = secrets.token_urlsafe(32)          # return raw token ONCE to the creator
token_hash = hashlib.sha256(token.encode()).hexdigest()
# read route: lookup by hash, reject if expires_at < now or revoked_at is not None,
# then delegate to the SAME graph assembly used by api/graph.py with
# visible_until_order=stored boundary, user_id=None  →  D-09, one filter path
```
*(stdlib `secrets`/`hashlib` — `[VERIFIED: Python 3.13 stdlib]`; label name is discretion.)*

### FakeLLMProvider-driven pipeline test (zero-cost chat verification)
```python
from backend.app.llm.provider import FakeLLMProvider, LLMEvent

def fake_provider() -> FakeLLMProvider:
    # per-call-index provider for mixed tool-call + cited-done scripts
    class Indexed(FakeLLMProvider):
        async def stream_chat(self, **kw):
            i = len(self.calls)
            for ev in (self.scripted_events[i] if i < len(self.scripted_events) else [LLMEvent.done("")]):
                yield ev
    return Indexed(scripted_events=[...])  # never touches the network
```
*(Pattern verified in `backend/tests/test_change_set_confirmation.py`; the per-call-index refinement is the skill's documented fix for same-events-every-call.)*

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `cose-bilkent` flat force layout | `cytoscape-fcose` compound/cluster layout | Phase 9 (D-03) | Real separation at 132-claim density (#57); new dep |
| Live shared Neo4j as the test target | Fresh CI Neo4j service container + scratch-series teardown | Phase 8 CI (08-07) → Phase 9 hardens (D-07) | Deterministic suites; AuraDB never polluted |
| `session:{user_id}:{int(now)}` ids + slide-on-read | `session:{uuid4()}` + background sweep | Phase 9 (PROB-03) | #9/#32 fixed |
| Global LLM settings node | BYOK headers (localStorage) + admin-gated fallback | Phase 8 (08-02/03) | #5 fixed; Phase 9 adds provider edge-case hardening (PROB-28) |

**Deprecated/outdated:**
- `cose-bilkent` remains installed but is superseded for this app by fcose (same family; keep the fallback path).
- `backend/requirements.txt`: generated `uv export` artifact duplicating `uv.lock` (#30) — delete or regenerate during REBRAND.
- Root `main.py` PyCharm template + `frontend/README.md` Vite boilerplate: delete (PROB-10).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | Full import-root rename `backend/` → `spoilerless/` is what D-12's "package dirs" means | REBRAND | If user only meant pyproject metadata, the extra sweep is wasted churn; flag as plan-check decision (Open Q1) |
| A2 | `fuse.js` SUS "too-new" is a metadata artifact; package is genuinely established | Package Audit | Low — recommendation avoids installing it anyway |
| A3 | Rendering AuraDB reseed (PROB-20) is safe via the idempotent MERGE-based setup script | PROB-20 | If seed files drifted from live data, reseed could overwrite; gate behind explicit plan + read-only pre-check (`scripts/aura_graph_integrity.sh`) |
| A4 | Zombie `:AppUser` rows are identifiable as test-created (no progress/ownership/session ties) | PROB-22 | If some rows are real users, sweep deletes them; never delete `ae8a41b7-...`; sweep script must print a dry-run count first |
| A5 | Render blueprint `name:` change creates a new service (operator must rename in dashboard) | REBRAND | If Render renames in place, operator step shrinks to a dashboard click; harmless either way |
| A6 | GitHub repo rename + `git remote set-url` is operator-touch and must be LAST | REBRAND/09-02 | Pushing to the old remote URL still works until renamed; sequence after 09-02 push |
| A7 | Error-code unification direction (uppercase canonical codes; validation errors also uppercased) is acceptable to the frontend normalization | PROB-09 | Contract tests + `client.ts` normalization must move together; see Open Q2 |
| A8 | `GraphCanvas.test.tsx` fixture stays the toy 11-node graph; assertions become count-independent | D-05 | If the fixture is enriched instead, all graph/App tests' counts change; recommend count-independent asserts only |

## Open Questions

1. **REBRAND-01 scope: full import-root rename or metadata-only?** What we know: D-12 lists "package dirs"; every `backend.app.*` import, `uv --project backend`, uvicorn module path, conftest sys.path, CI, and render `startCommand` reference the `backend/` root. What's unclear: whether the user wants the Python import root physically renamed (large mechanical sweep, fully gated by CI) or only the package metadata + all user-visible names. Recommendation: full rename in the wave-0 plan (matches "package dirs" literally, "all lets go fast"), with the metadata-only subset as the documented fallback if plan-check objects.
2. **Error-code casing direction (#20/PROB-09).** What we know: `ErrorDetail.code` regex is lowercase-only while the API emits uppercase `AUTH_*`/`LLM_*` codes; pydantic validation errors emit lowercase (`invalid_request`). What's unclear: which canonical form. Recommendation: uppercase canonical codes (`AUTH_UNAUTHENTICATED`, `INVALID_REQUEST`, ...), update the regex to `^[A-Z][A-Z0-9_]*$`, update `client.ts` normalization + `test_openapi_contract.py` together in one plan.
3. **09-02 exact scope.** What we know (VERIFIED this session): `ci-smoke-test` branch does NOT exist locally or on the remote; the eslint config fixes are already in local `main`; local main is 4 commits ahead of `origin/main` (`288743e`). What's unclear: whether a CI re-run on main has ever been confirmed. Recommendation: plan 09-02 as "push main → confirm GitHub Actions green on main → close any new failures" — a git-state check FIRST, not a branch merge.
4. **PROB-20 live reseed timing.** Autonomous plan vs operator wave. Recommendation: put the reseed (or startup schema check) in the final operator wave alongside 09-03/09-04, with a read-only `scripts/aura_graph_integrity.sh` audit before and after — it mutates the shared live DB.
5. **FEAT-04 dashboard vs dropdown** and **FEAT-02 tab placement** — Claude's discretion, resolved in planning (CONTEXT's default: keep dropdown + add dashboard entry; tabbed timeline).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Local docker Neo4j | scratch-scoped live-DB tests locally | ✓ (compose recipe) | 2026.06.0-community | CI service container (same image, pinned) |
| CI Neo4j service container | full backend suite gate | ✓ (ci.yml exists) | 2026.06.0-community | — |
| AuraDB Free (shared) | read-only audits + operator UAT only | ✓ | — | local docker during cooldown (Pitfall 1) |
| Upstash Redis | 09-04 live 429/cache verification | ✓ (URL from 08-01 user_setup) | — | rate limiting disabled by design when `redis_url` empty |
| FakeLLMProvider | all chat/LLM tests | ✓ (in prod source) | — | never live LLM spend |
| `npm` registry | cytoscape-fcose install | ✓ | 2.2.0 | cose fallback |

**Missing dependencies with no fallback:** none — the phase is explicitly scoped to the free stack; any paid service/API is out of scope by constraint.
**Missing dependencies with fallback:** GitHub Actions runner (only triggerable by push/PR — 09-02 needs the operator's repo push approval, hence operator-wave).

## Validation Architecture

> `nyquist_validation: true` in `.planning/config.json` [VERIFIED]. Full suite NEVER runs against live AuraDB — CI's fresh container is the only full-suite target (Phase 8 precedent, Pitfall 1).

### Test Framework

| Property | Value |
|---|---|
| Framework | `pytest` 9.1.1+ (backend, `pyproject.toml` dev group); `vitest` 4.1.10+ (frontend, `frontend/package.json`) [VERIFIED: STACK.md] |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`, `testpaths = ["backend/tests"]`); `frontend/vite.config.ts` (jsdom, setup.ts) |
| Quick run command | `uv run pytest backend/tests/test_<file>.py -x` (backend); `cd frontend && npx vitest run <file>` (frontend) |
| Full suite command | `uv run pytest` (backend, from repo root); `cd frontend && NODE_ENV=test CI=1 npm run test` + `npm run build` + `npm run lint` |

### Phase Requirements → Test Map (representative — planner expands per plan)

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| PROB-01/02/26 | mutation routes require owner; records carry `user_id`/`created_by` | integration | `uv run pytest backend/tests/test_user_content_api.py -x` | ✅ extend |
| PROB-03 | uuid4 session ids + sweep | integration/unit | `uv run pytest backend/tests/test_session_repository.py -x` | ✅ extend |
| PROB-06/22 | scratch-series isolation; zombie sweep script; CI pollution gate | integration + CI | `uv run pytest backend/tests/test_seed_idempotency.py -x`; ci.yml step | ✅ extend + CI |
| PROB-08 | lint 0 errors; stale refs fixed | lint gate | `cd frontend && npm run lint` | ✅ gate exists |
| PROB-12/34 | approve/reject return real persisted `revision_id`; revisions carry `user_id` | unit/integration | `uv run pytest backend/tests/test_candidate_review.py -x` | ✅ extend |
| PROB-13 | mid-stream failure marks turn failed + logs | integration | `uv run pytest backend/tests/test_chat_api.py -x` | ✅ extend |
| PROB-14/23 | `ProductionGoogleVerifier` behavioral test (garbage token + MockTransport); FE wire-shape tests not mocking the client | unit | new `backend/tests/test_google_verifier.py`; `frontend/src/api/progress.test.ts` wire-shape | ❌ Wave 0 |
| PROB-15/31 | progress payload shapes; locked-episode click regression | FE unit | `cd frontend && npx vitest run src/hooks/useWatchProgress.test.tsx` | ✅ extend |
| PROB-24 | notes enter assembled context | integration | `uv run pytest backend/tests/test_retrieval_pipeline.py -x` | ✅ extend |
| PROB-25 | one visibility-derivation rule both paths | integration | `uv run pytest backend/tests/test_change_set_api.py -x` | ✅ extend |
| PROB-32/FEAT-11 | fcose layout, filters, focus reducer, count-independent asserts | FE unit | `cd frontend && npx vitest run src/components/graph/GraphCanvas.test.tsx` | ✅ extend |
| FEAT-01/07/08 | search/palette over visible payload | FE unit | `cd frontend && npx vitest run src/components/graph/*.test.tsx` | ❌ Wave 3 |
| FEAT-05 | Markdown export reuses filtered path | integration | `uv run pytest backend/tests/test_graph_api.py -x` | ✅ extend |
| FEAT-06 | path route calls allowlisted executor | integration | `uv run pytest backend/tests/test_graph_api.py -x` | ✅ extend |
| FEAT-09 | token-gated snapshot = same filter path; expiry/revoke | integration | new `backend/tests/test_share_api.py` | ❌ Wave 0 |
| REBRAND-01 | zero `hdgrafcehennemi` hits in product/docs files | grep gate | `git grep -il 'hdgrafcehennemi'` (excluding `.planning/` + PROBLEMS.md trail) | ❌ Wave 0 (in rename plan) |
| DOCS-04 | API.md regenerated from live openapi (45/33); ARCHITECTURE/ROADMAP corrected | doc contract | `uv run pytest backend/tests/test_frontend_contract_doc.py -x` + regen script | ✅ extend |

### Sampling Rate
- **Per task commit:** targeted `uv run pytest backend/tests/test_<affected>.py -x` and/or `cd frontend && npx vitest run <file>`
- **Per wave merge:** `uv run pytest` (full backend — against local docker/CI container, never AuraDB), `cd frontend && NODE_ENV=test CI=1 npm run test`, `npm run build`, `npm run lint`
- **Phase gate:** full suite green + `git grep -il 'hdgrafcehennemi'` clean + operator UAT (09-02/09-03/09-04) before `/gsd-verify-work`; `human_verify_mode: "end-of-phase"` is the configured mode

### Wave 0 Gaps
- [ ] `backend/tests/test_google_verifier.py` — real `ProductionGoogleVerifier` behavioral test (PROB-23: garbage token + `httpx.MockTransport`, assert `GoogleVerificationError`/`GoogleTransportError` mapping, never NameError)
- [ ] `backend/tests/test_share_api.py` — FEAT-09 token lifecycle (create/read/expiry/revoke/reuse-same-filter)
- [ ] `backend/tests/test_user_content_api.py` wire-shape progress regression (PROB-15/31 payload shapes)
- [ ] `frontend/src/api/progress.test.ts` wire-shape tests WITHOUT mocking the API client (PROB-23 class)
- [ ] Rename sweep verification gate (REBRAND-01 grep command above)
- [ ] CI DB-pollution gate (PROB-22: post-suite residue check in `ci.yml`)

## Security Domain

> `security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: high` [VERIFIED: `.planning/config.json`].

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | yes | Google ID-token verification stays; PROB-23 adds the behavioral test that locks it; PROB-30 fixes client-id/env drift (the #42 audience-mismatch trigger class) |
| V3 Session Management | yes | PROB-03: uuid4 ids, no slide-on-read, background sweep (kills unbounded growth + same-second collision) |
| V4 Access Control | yes | PROB-01/02/26: `require_current_user` on all mutations + owner binding + `created_by`; PROB-12: revisions carry actor; admin gates already live (Phase 8) |
| V5 Input Validation | yes | Pydantic strict models; PROB-16 (`None` order → 422, not 500); PROB-19 whitespace-only keys rejected server-side |
| V6 Cryptography | yes | `secrets.token_urlsafe` for share tokens; store token HASH in Neo4j (never the raw token); TLS everywhere (existing rediss:///neo4j+s:// normalization) |
| V8 Data Protection | yes | Owner scoping on user content (PROB-02); zombie-data sweep (PROB-22) — note: sweeping 3,855 users is also a data-retention improvement |
| V13 API and Web Service | yes | PROB-09 error-code contract; PROB-17 baseline security headers (CSP/HSTS/X-Content-Type-Options/X-Frame-Options/Referrer-Policy) + CORS wildcard-with-credentials narrowed; PROB-21 error boundary; FEAT-09 token-gated route must appear in the OpenAPI contract test |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Share-link becoming a second, looser spoiler path | Information Disclosure | D-09 hard rule: token route calls the SAME graph assembly as `api/graph.py`; snapshot-at-creation means boundary is frozen at creation; expiry+revocation |
| Anonymous boundary bypass (client-chosen `visible_until_order`) | Tampering | PROB-04/05: anonymous = fixed boundary (order 1), candidates require resolved server-side boundary |
| CSRF on new state-changing routes (share-token revoke, export) | Tampering | REVOKE endpoint is authenticated → `verify_origin` strict dependency (Phase 8 pattern); export is GET (read-only, boundary-fixed) |
| BYOK base_url SSRF | Information Disclosure | Already reduced to self-exfiltration (Phase 8); PROB-28 adds `JSONDecodeError` parity and caps replayed tool results (cost bloat) |
| Zombie-sweep deleting real user rows | Availability / Data Integrity | Dry-run count first; never delete `ae8a41b7-db96-40e8-b6c2-2e3c69aedb11`; delete only rows with no progress/chat/ownership ties (PROB-22, A4) |
| Rate-limit bypass during 09-04 verification | DoS | 09-04 is a live verification, not a load test — bounded, scripted checks (a handful of rapid requests), then stop; AuraDB/Upstash free-tier cooldown awareness |

## Wave / Sequencing Guidance (operator-touch LAST)

Constraint: 09-02, 09-03, 09-04 require the operator's account access → ALL autonomous work precedes them; the final wave is `checkpoint:human-action` for all three. Batch aggressively (`granularity: coarse`, "all lets go fast").

- **Wave 0 — Rename + repo state (autonomous, FIRST per D-12):** REBRAND-01 full sweep (import root decision per Open Q1) + git-state check/push prep (4-commit gap vs origin/main). Gate: `git grep -il 'hdgrafcehennemi'` clean (excl. `.planning/` + PROBLEMS trail), full suite green post-rename. Also Wave 0: PROB-23 test scaffolding (verifier behavioral test + wire-shape tests) — the cheapest regression net for the two most dangerous bug classes.
- **Wave 1 — Backend correctness clusters (autonomous):** Auth/ownership: PROB-01/02/03/04/05/09/12/14/15/16/25/26/27 (one or two plans — they share files: `api/user_content.py`, `api/candidates.py`, `api/revisions.py`, `repository/session.py`, `domain/*`). Chat/LLM: PROB-13/24/28. Read-path nits + env: PROB-29/30. Each with scratch-scoped tests. PROB-31 (#56 progress hook) can start here (frontend) — it gates FEAT-03.
- **Wave 2 — Test isolation + infra (autonomous):** PROB-06/22 (candidate tests → scratch series, teardown fixtures, one-time zombie sweep SCRIPT with dry-run, CI DB-pollution gate), PROB-07 (flaky App e2e), PROB-08/09-06 (lint 0 + fix stale refs), PROB-18 (direct unit tests), PROB-19 (small trust fixes), PROB-20 prep (read-only integrity audit; reseed itself → operator wave).
- **Wave 3 — Frontend features (autonomous, after PROB-31):** FEAT-01/07/08 (shared search/palette — substring, zero deps), FEAT-02 timeline (tabbed), FEAT-03 new-reveal highlight (needs PROB-31's hook fixed first), FEAT-04 dashboard (augment dropdown), FEAT-05 Markdown export + FEAT-06 path route (backend routes, one plan), FEAT-10 mobile/responsive, FEAT-09 share links (backend+frontend, one plan), PROB-21 error boundary. **PROB-32 + FEAT-11 (fcose overhaul) LAST in this wave** — biggest frontend risk, extracted modules per D-06, count-independent test fixes per D-05.
- **Wave 4 — Docs (autonomous):** DOCS-04 (regenerate API.md from live openapi 45/33; fix ARCHITECTURE ChangeSet/known-gaps; fix ROADMAP deferrals), PROB-10 (junk removal + MIT LICENSE + Fandom images self-host/drop), PROB-21 doc/log cleanup leftovers, PROB-29's `docs/DEVELOPMENT.md:50` fix.
- **FINAL WAVE — Operator-touch (`checkpoint:human-action`, LAST by constraint):**
  1. **09-02** — push local main to origin; confirm GitHub Actions green on main (backend + frontend jobs); close any new failures.
  2. **09-03** — operator supplies `ADMIN_EMAILS` value; set on Render; live admin-role check (candidate approve/reject/edit + ChangeSet confirm admin-gated, non-admin 403).
  3. **09-04** — set `REDIS_URL` (Upstash `rediss://`) on Render; live 429 rate-limit + graph-cache invalidation verification (bounded scripted checks).
  4. **PROB-20** — live reseed (idempotent MERGE script) or startup schema check, with `aura_graph_integrity.sh` before/after.
  5. **PROB-22 sweep execution** (dry-run → approve → run) if not already executed in Wave 2.
  6. **REBRAND operator steps** — GitHub repo rename + `git remote set-url`, Render service rename, UptimeRobot monitor rename (A6).
  - 09-07 (full CI/CD) and 09-08 (observability) are deferred-OPS carry-overs: they are autonomous code/config work but depend on live-stack confirmation — plan them as small autonomous plans in Wave 2/4 with the live confirmation folded into the final wave, OR defer to Phase 10 backlog per CONTEXT D-14's "folded" language; recommend folding their code artifacts (dependency scan step, runbook docs) into Wave 2/4 and leaving platform wiring to the operator wave.

## Sources

### Primary (HIGH confidence — read/verified directly this session)
- `.planning/phases/09-feature-expansion-full-audit-remediation/09-CONTEXT.md`, `09-DISCUSSION-LOG.md`
- `.planning/REQUIREMENTS.md` (PROB-01..32, FEAT-01..10, FEAT-11, DOCS-04, REBRAND-01), `.planning/ROADMAP.md` §Phase 9, `.planning/STATE.md`, `.planning/config.json`
- `docs/PROBLEMS.md` (all 57 findings, canonical ledger), `docs/FEATURE-IDEAS.md`, `docs/FEATURE-RESEARCH.md`, `docs/PROJECT-SPEC.md` (§3/§6/§7), `docs/DEVELOPMENT.md` (line 50 drift)
- `.planning/codebase/STACK.md`, `TESTING.md`, `STRUCTURE.md`
- `.planning/phases/08-production-deployment-automated-ci-cd/08-CONTEXT.md`, `08-VERIFICATION.md`, `08-RESEARCH.md`
- Live tree: `frontend/package.json`, `frontend/eslint.config.js`, `frontend/vite.config.ts`, `frontend/src/components/graph/GraphCanvas.tsx` (+ test), `frontend/src/hooks/useWatchProgress.ts`, `frontend/src/lib/byok.ts`, `frontend/index.html`, `index.html`, `backend/app/main.py`, `backend/app/services/auth.py`, `backend/app/llm/provider.py` (FakeLLMProvider), `backend/app/retrieval/pipeline.py`, `backend/tests/test_retrieval_tools.py`, `backend/tests/test_candidate_ingest.py`, `backend/tests/test_graph_api.py`, `.github/workflows/ci.yml`, `render.yaml`, `docker-compose.yml`, `pyproject.toml`, `backend/scripts/smoke.sh`, `data/dexter/seed/characters.json`, `git log`/`git status`/`git remote`/`git ls-remote`
- npm registry: `npm view cytoscape-fcose` + `gsd-tools query package-legitimacy check` (OK), `npm view fuse.js` (SUS)

### Secondary (MEDIUM confidence)
- Skill runbooks (`hdgrafcehennemi` + `hdgrafcehennemi-pitfalls` refs): `08-ci-test-drift.md`, `08-01-deploy-build-traps.md`, `08-02-frontend-byok-vitest.md`, `auradb-free-and-neo4j-tls-08-04.md`, `pre-public-release-audit-2026-08-04.md` — cited as [VERIFIED: skill] where they record live-verified incidents
- Cytoscape.js fcose docs — `[CITED: js.cytoscape.org/#layouts/fcose]` (option names; tuning is discretion)

### Tertiary (LOW confidence — flagged in Assumptions Log)
- Render blueprint `name:`-change semantics (A5), GitHub repo-rename mechanics (A6), fuse.js metadata anomaly (A2)
