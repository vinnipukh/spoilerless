# HD Graf Cehennemi

## What This Is

A spoiler-safe narrative knowledge graph for TV series with a grounded conversational agent. v1.1 covers Dexter Season 1, Episodes 1–3 and lets an authenticated user explore source-backed narrative knowledge, control the visible episode boundary, add personal knowledge, inspect/revert revisions, ask questions answered only from graph data visible up to their watch progress (with clickable citations and graph highlighting), and safely propose graph edits through a typed confirm-before-apply ChangeSet flow.

## Core Value

Users can safely explore a TV-series knowledge graph — and now chat about it — without ever seeing information beyond their selected watch progress, because filtering occurs in the backend before data reaches the frontend, the LLM, or any tool call. No raw Cypher ever reaches the model, and no graph write happens without explicit human confirmation.

## Current State (v1.1 shipped 2026-08-02, supersedes v1.0)

- Neo4j + FastAPI backend, Google OAuth authentication, real health checks, idempotent seed setup.
- React + TypeScript + Cytoscape frontend: series/episode selection, watch-progress confirmation gate, graph exploration, tabbed detail inspector, cinematic visual system.
- User notes and custom nodes/relationships, visually and structurally distinct from canonical/candidate content.
- Append-only revision history with inspect/revert.
- Candidate-claim extraction-preparation layer: structured JSON contract, review UI (approve/reject/edit), source-connector interface — accepts fixtures only, no live ingestion or LLM extraction.
- Full spoiler-safe GraphRAG chat agent: ten allowlisted retrieval tools, an LLM provider abstraction (OpenAI-compatible + Gemini + fake test double), a deterministic retrieval→context→answer→citation pipeline, a versioned system prompt treating all graph-sourced text as untrusted, and a typed two-stage ChangeSet propose/confirm/revert flow with auditable Revision logging.
- ~23,300 LOC across `backend/app` and `frontend/src`. Python 3.13 + FastAPI + Pydantic v2 + Neo4j async driver; React 19 + TypeScript + Vite + Cytoscape.js; `uv` for Python packaging.

**Known outstanding issue (not blocking v1.1, tracked as follow-up):** the Settings feature (`/api/settings/llm`) stores a single global, non-per-user LLM provider config, and `base_url` scheme validation was added but full SSRF/cross-user-takeover protection (per-user scoping or admin gate) is deferred. See `.planning/milestones/v1.1-phases/06-spoiler-safe-graphrag-chat-and-graph-editing-agent/06-SECURITY.md`.

## Requirements

### Validated

- ✓ Local Neo4j/FastAPI/React infrastructure with real health checks and idempotent setup — v1.0
- ✓ Dexter Series/Episode metadata graph and endpoints — v1.0
- ✓ Manually curated evidence-backed seed graph with spoiler visibility metadata — v1.0
- ✓ Backend-enforced spoiler-aware graph API (data-access-layer filtering) — v1.0
- ✓ React/Cytoscape graph experience with watch-progress confirmation — v1.0
- ✓ User notes and custom node/relationship creation, distinct from canonical content — v1.0
- ✓ Append-only revision history with revert — v1.0
- ✓ Extraction-preparation contracts, candidate review workflow, source-connector interface (no live ingestion) — v1.0
- ✓ Google OAuth authentication (single real-user model, no roles yet) — v1.0
- ✓ Spoiler-safe GraphRAG chat: allowlisted retrieval tools, LLM provider abstraction, citation-validated grounded answers — v1.1
- ✓ Typed ChangeSet propose/confirm/revert graph-editing flow with auditable Revision — v1.1

### Active

- [ ] Per-user or admin-gated scoping for the LLM Settings feature, plus full SSRF protection on `base_url` (partial fix landed: non-http(s) schemes rejected; DNS/IP-based redirection and cross-user config takeover remain open)
- [ ] CI/CD pipeline (currently all testing is manual/local per `docs/TESTING.md`)
- [ ] Resolve pre-existing test-pollution debt in `test_seed_idempotency.py` (untorn-down candidate-origin fixture from `test_candidate_ingest.py`)
- [ ] Clean up pre-existing frontend lint debt (28 errors, none newly introduced in v1.1)

### Out of Scope

- Automated ingestion/extraction from OpenSubtitles, scripts/PDFs, podcasts, Fandom/IMDb/news, or other external sites — still no live source retrieval, only the fixture-driven candidate contract
- Multi-user roles/admin concepts — no role infrastructure exists yet; this is why the Settings-scoping fix above is deferred rather than trivial
- Production deployment, public hosting, mobile/social features — prototype phase per `docs/DEPLOYMENT.md`

## Constraints

- **Spoiler safety:** every exposed graph element carries `visible_from_order`; the backend filters before returning data to the frontend, the LLM, or any tool call. Hidden names, labels, evidence, and aggregate counts must not leak.
- **No raw Cypher to the LLM:** the model's only actions are typed, allowlisted retrieval tool calls and typed ChangeSet proposals — never a text-to-Cypher surface.
- **Writes require human confirmation:** the model may only *propose* a ChangeSet; a human must explicitly confirm before any transaction touches the graph.
- **Provenance:** automatic/candidate claims require EvidenceFragments with source, episode, locator, retrieval metadata, and content hash where possible. Manually curated seed claims are evidence-backed.
- **Separation:** canonical, candidate/automatic, and user-created content are represented and displayed distinctly; the assistant can never mutate canonical/candidate content directly.
- **History:** edits and reverts append revisions; history is not destroyed.
- **Local stack:** Neo4j, FastAPI/Pydantic, React 19 + TypeScript + Vite + Cytoscape.js; Python packaging through `uv`.
- **Single-user model today:** Google OAuth exists, but there is no role/admin concept — a real constraint on how any shared-config feature (like LLM Settings) can be safely scoped.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Root `ROADMAP.md` defined Prototype v0 scope | Prevent planning documents from narrowing the canonical demo | ✓ Good — v0 shipped in full |
| Neo4j as graph source of truth | Graph-native storage fits connected narrative data | ✓ Good |
| Backend/data-access spoiler filtering | Downstream clients (frontend, LLM) must never receive future data | ✓ Good — held through the entire GraphRAG chat addition with zero leakage found in verification |
| Evidence-backed atomic claims | Users can understand why knowledge exists | ✓ Good |
| Separate user/candidate/canonical content | Preserves provenance and supports correction | ✓ Good — extended cleanly to ChangeSet origin protection in v1.1 |
| Simplified append-only revision log | Meets history/revert needs without Git-like graph versioning | ✓ Good — extended cleanly to ChangeSet apply/revert |
| Extraction contracts before extraction automation | Keeps the model extensible while actual extraction remains post-v0 | ✓ Good |
| Ten allowlisted typed retrieval tools, no raw Cypher to LLM | Eliminates the entire text-to-Cypher injection class structurally | ✓ Good — confirmed by prompt-injection test suite and security audit |
| Two-stage ChangeSet propose/confirm, never auto-apply | A human must gate every graph write the assistant suggests | ✓ Good |
| Global (non-per-user) LLM Settings, built without a threat model | Fastest path to a working Settings UI given no role infrastructure existed | ⚠️ Revisit — flagged by security audit as an unregistered SSRF/cross-user-takeover surface; partial fix (scheme validation) landed, full scoping deferred |

---
*Last updated: 2026-08-02 after v1.1 milestone*
