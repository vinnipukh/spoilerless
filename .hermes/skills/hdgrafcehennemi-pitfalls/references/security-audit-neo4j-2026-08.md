# hdgrafcehennemi — Neo4j graph-layer security audit (2026-08-14, subagent S5)

Static-analysis audit of the spoiler boundary + Neo4j layer. Full findings (SEC-GR-001..016, complete 51-query inventory, per-route boundary matrix): `.planning/quick/20260814-security-audit/findings/S5-neo4j.md`. These facts are the durable architecture; the weak surfaces were unpatched at audit time.

## Boundary model (durable architecture invariants)

- **Read predicates are fail-closed in Cypher**: `visible_from_order IS NOT NULL AND visible_from_order <= $visible_until_order` everywhere; single definition `visible_claim_where()` in `spoilerless/app/spoiler/filter.py` (origin allowlist `['canonical','candidate']`, excludes `claim_type = 'user_authored'`, validity-window check). Never reimplement per-query.
- **Effective boundary**: `spoiler/policy.py::resolve_effective_boundary` = `min(requested, view_as_of_order, watched_through_order)`; anonymous readers FIXED at order 1 (PROB-04/#12); `api/graph.py::_resolve_effective_boundary` is the shared resolver every new read route must route through (auth-optional routes: anon=1, auth=clamped; no client-trusted orders).
- **Query homes**: `spoiler/filter.py` (graph read), `retrieval/tools.py` (RAG tools; `visible_until_order`/`user_id`/`series_id` server-injected, never from model args), `graph/*.py` (chat/progress/change_set), `repository/*.py` (user_content/settings), `revisions/__init__.py`, `graph/candidates.py`.
- **Cache** (`cache/graph_cache.py`): keys `graph:{series}:{effective_boundary}:{user_id|anon}`; viz keys add `view:projection_version:epoch:focus_sig`; epoch bump + scan-delete (`graph:{id}:*`, `viz:{id}:*`) on content writes; expansion path intentionally uncached; viz DTO re-validated against key metadata on read.
- **Credentials**: app connects as the **AuraDB instance admin principal** (Aura Free has no scoped roles) — `NEO4J_USERNAME=<instance-id>` in `.env`. Runtime performs DETACH DELETE sweeps (`:Session`, `:ShareToken`).
- **Sessions**: 48-byte random tokens, SHA-256 hashed at rest, `:Session` nodes, hourly sweep, no slide-on-read. Share tokens 32 bytes, hashed.
- **LLM key**: plaintext JSON property on `:AppSetting{key:'llm'}`; GET returns masked only; PUT admin+CSRF gated; any authenticated user can SPEND the stored key via chat (BYOK headers `X-LLM-*` exist as the alternative).

## Known weak surfaces (SEC-GR-004..008 — unpatched at audit time)

- **Candidates ingest** (`POST /candidates/ingest`, any AUTHENTICATED user): `visible_from_order`/valid window client-supplied, predicate/evidence_text free text → injected claims are origin `candidate` and render in EVERYONE's graph + LLM context at any boundary ≥ client value (origin allowlist includes `candidate`). Graph poisoning / spoiler injection / cross-user prompt injection.
- **Candidates read** (list/get): NO auth, boundary client-chosen, no anonymous-order-1 rule, no progress clamp.
- **Revisions read** (list/get): NO auth, boundary client-chosen, **no persisted-episode validation at all**; returns `before`/`after` snapshots of user content + actor `user_id`.
- **Notes read** (list/get): NO auth; `NOTE_LIST_QUERIES`/`NOTE_GET_QUERIES` (`repository/user_content.py`) have **no `user_id` filter** → all users' notes readable (contrast: retrieval tool `get_user_notes` IS user-scoped).
- **Write endpoints as oracle**: note/relationship create require only `visible_from_order >= 1` (no `<= boundary` cap) and return the target's `visible_from_order`; seed ids are deterministic/guessable (`dexter:claim:s01e01:...`, `dexter:character:rita_morgan`) → existence + reveal-order oracle for hidden future nodes.
- **Progress POST** = self-attestation: any user sets `watched_through_order` to any persisted episode order (validated only against persisted orders).

## Reusable audit checklist (graph-backed apps)

1. Enumerate every `tx.run(`/`execute_query`; grep for f-strings/`.format(`/`+` inside Cypher; verify all interpolation is over closed server-owned enums/literals.
2. LLM tool surface: any text2cypher or raw-query tool? Server-inject the boundary/user_id into tool kwargs; pydantic-validate args; never trust model-supplied visibility.
3. DB principal role: admin? scoped role available? (Aura Free: no.)
4. Per read route: auth? boundary source (client vs server)? anonymous rule? progress clamp? persisted-episode validation? (matrix in findings file.)
5. Cache: keys carry series+boundary+user(+version/epoch/focus)? invalidation on content writes? any uncached-for-identity surfaces?
6. Settings write path: masking, admin gate, key at rest, who can spend the shared key.
7. User content → shared graph / other users' LLM context channels (prompt injection, stored-XSS data flow).
