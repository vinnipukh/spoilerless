# Phase 9: Feature Expansion & Full Audit Remediation — Pattern Map

**Mapped:** 2026-08-05
**Files analyzed:** 54 (31 frontend create/modify from UI-SPEC manifest + 18 backend create/modify from CONTEXT/RESEARCH + 5 shared infra/docs)
**Analogs found:** 50 / 54 (4 no-analog — all new-domain leaf components with role-match analogs)

> Consumed by `gsd-planner`. Every excerpt below is read from the LIVE tree at `288743e`-era local main this session. Line numbers are current. **search_files is broken on this MSYS host — use `rg` via terminal.** Never re-derive visibility logic: the ONE filter shape is `visible_from_order IS NOT NULL AND visible_from_order <= $visible_until_order` (spoiler/filter.py + skill).

## File Classification

### Backend — New files

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/app/api/share.py` (FEAT-09) | controller (route) | request-response | `backend/app/api/graph.py` (read path) + `api/user_content.py` (route skeleton) | exact |
| `backend/app/repository/share.py` (FEAT-09, D-10) | repository | CRUD | `backend/app/repository/session.py` (token hash + expiry) | exact |
| `backend/app/domain/share.py` (FEAT-09) | model (domain contract) | transform | `backend/app/domain/user_content.py` (`VisibleUntilOrder`, strict models) | role-match |
| `backend/tests/test_share_api.py` (FEAT-09) | test | request-response | `backend/tests/test_graph_api.py` (TestClient + live DB) | exact |
| `backend/tests/test_google_verifier.py` (PROB-23) | test | unit (behavioral) | `services/auth.py` `ProductionGoogleVerifier` + `httpx.MockTransport` | exact |
| `backend/app/spoiler/visibility.py` or `services/visibility.py` (PROB-25 shared rule) | service/utility | transform | `spoiler/policy.py::effective_view_order` + `repository/change_set.py` stamping | role-match |
| `backend/scripts/zombie_sweep.sh|py` (PROB-22) | script | batch | `scripts/aura_graph_integrity.sh` (read-only audit) + session.py docstring sweep Cypher | role-match |

### Backend — Modified files

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/app/repository/user_content.py` (PROB-01/02/25/26) | repository | CRUD | itself (748L — add `created_by`, unify visibility derivation) | exact |
| `backend/app/api/user_content.py` (PROB-25/26) | controller | request-response | itself (250L — add `CurrentUserDependency`, pass user into repo) | exact |
| `backend/app/repository/change_set.py` (PROB-25/27, 828L) | repository | CRUD/transaction | itself + `api/revisions.py` revert pattern (`apply_revision_id`+`revert_revision_id`) | exact |
| `backend/app/graph/change_set.py` (PROB-25/27, 348L) | model/query | transform | itself (Cypher constants + 13-op union in `domain/change_set.py`) | exact |
| `backend/app/api/candidates.py` (PROB-12/33) | controller | request-response | itself (335L — return REAL persisted `revision_id`, not the precomputed `rev_id`) | exact |
| `backend/app/api/revisions.py` (PROB-12/33) | controller | request-response | itself (280L — list/get/revert) | exact |
| `backend/app/repository/session.py` (PROB-03, PROB-22 sweep) | repository | CRUD | itself (271L — swap id scheme, add sweep method) | exact |
| `backend/app/services/auth.py` (PROB-03 sweep job, PROB-23) | service | request-response | itself (183L — `AuthService`, `ProductionGoogleVerifier`) | exact |
| `backend/app/retrieval/pipeline.py` (PROB-24) | service | transform | itself (980L — `_accumulate`/`_finalize`/`assemble_context`) | exact |
| `backend/app/retrieval/tools.py` (PROB-24 `user_id` thread) | service | transform | itself (852L — `get_user_notes`) | exact |
| `backend/app/llm/provider.py` (PROB-28) | service | streaming | itself (`OpenAICompatibleProvider`, `FakeLLMProvider` @ :415) | exact |
| `backend/app/spoiler/filter.py` (PROB-29) | query module | transform | itself (215L — add `series_id` to `SOURCES_QUERY`/`EVIDENCE_QUERY` MATCH) | exact |
| `backend/app/core/errors.py` (PROB-09) | middleware/utility | transform | itself (179L — `ErrorDetail.code` regex `^[a-z][a-z0-9_]*$` at :28) | exact |
| `backend/app/core/config.py` (PROB-30) | config | — | itself (147L — `Settings` fields) | exact |
| `backend/app/graph/seed.py` (PROB-20/22, ShareToken constraint) | model/seed | batch | itself (397L — constraint/index block at :134-228, `setup_database` :377) | exact |
| `backend/app/main.py` (REBRAND `SERVICE_NAME`, share router, sweep lifespan) | entry | — | itself (`SERVICE_NAME = "hdgrafcehennemi-backend"` — /health field) | exact |
| `backend/tests/test_candidate_ingest.py` + `test_seed_idempotency.py` + `test_graph_api.py:101` (PROB-06/22, REBRAND) | test | — | `backend/tests/test_retrieval_tools.py:74-75` (scratch-series) | exact |
| `.github/workflows/ci.yml` (PROB-22 DB-pollution gate, 09-07 dep scan) | config | batch | itself (backend+frontend jobs, Neo4j service container) | exact |

### Frontend — New files (all paths under `frontend/src/`)

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `components/graph/layoutConfig.ts` (D-03/D-04) | utility (layout config) | transform | `GraphCanvas.tsx:33-87` (`layoutOptionsFor`, registration try/catch) | exact (extract from) |
| `components/graph/filterState.ts` (D-04) | store (client state) | transform | `lib/byok.ts` (module-level persist helpers) + `useGraph.ts` key pattern | role-match |
| `components/graph/focusReducer.ts` (D-04) | reducer | transform | `GraphCanvas.tsx:346-397` (`.faded`/`.selected-dominant` class logic) | exact (extract from) |
| `components/graph/GraphFilterPanel.tsx` (FEAT-11/PROB-32) | component | request-response (UI) | `GraphLegend.tsx` (type chips + `NODE_TYPES`) + `EpisodeSelector.tsx` (pill ToggleGroup) | role-match |
| `components/graph/NodeSearch.tsx` (FEAT-01/07) | component | request-response (UI) | `GraphControls.tsx` (overlay button stack) + `CommandPalette` spec | role-match |
| `components/graph/NodeHoverCard.tsx` (FEAT-11) | component | UI | `frontend/src/components/ui/card` + GraphLegend badge patterns | role-match |
| `components/graph/PathFinder.tsx` (FEAT-06) | component | request-response | `GraphControls.tsx` (mode chip + button) + `GraphFocusIndicator` (mode chip precedent) | role-match |
| `components/timeline/TimelineView.tsx` + `TimelineEventRow.tsx` (FEAT-02) | component | request-response (UI) | `SettingsPage.tsx` (full-canvas view) + `DetailPanel.tsx` rows | role-match |
| `components/series/SeriesDashboard.tsx` (FEAT-04) | component | request-response | `SettingsPage.tsx` (dialog/card layout) + existing `Dialog` primitives | role-match |
| `components/palette/CommandPalette.tsx` (FEAT-08) | component | request-response (UI) | `Dialog` primitives + `NodeSearch` index (shared `searchIndex.ts`) | role-match |
| `components/share/ShareDialog.tsx` (FEAT-09) | component | request-response | `SettingsPage.tsx` (dialog with list rows + destructive buttons) | role-match |
| `components/share/ShareView.tsx` (FEAT-09) | component (read-only shell) | request-response | `AppShell.tsx` (minimal header) + `GraphCanvas` readOnly prop branch | role-match |
| `components/detail/BacklinksTab.tsx` (FEAT-11) | component | request-response (UI) | `DetailPanel.tsx` tabs (existing Claims/History tab row patterns) | role-match |
| `lib/searchIndex.ts` (FEAT-01/07/08) | utility | transform | `graphElements.ts` (pure mapping over `GraphResponse`) | exact (same input type) |
| `lib/exportMarkdown.ts` (FEAT-05) | utility | transform | `lib/utils.ts` (pure helpers) — client fallback only | role-match |
| `api/share.ts`, `api/export.ts` (FEAT-09/05) | client | request-response | `api/graph.ts` (6L — `apiFetch` one-liner) + `api/progress.ts` (body-shape builder) | exact |
| `hooks/useHotkey.ts` (FEAT-08) | hook | event-driven | `GraphCanvas.tsx:29-31` (module-scope `matchMedia` capture) | role-match |
| `types/share.ts` (FEAT-09), `types/cytoscape-fcose.d.ts` (D-03) | type | — | `types/graph.ts` (wire mirror) + `types/cytoscape-cose-bilkent.d.ts` (6L `Ext` shim) | exact |
| `components/{graph,timeline,series,palette,share}/*.test.tsx` | test | — | co-located `<subject>.test.tsx` convention; wire-shape tests per `api/chat.test.ts` (fetch stub, NO `vi.mock` of client) | exact |

### Frontend — Modified files

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `components/graph/GraphCanvas.tsx` (PROB-32, D-03..D-06) | component (god-file) | request-response (UI) | itself (530L — swap layout at :33-87, add `readOnly`/`newlyRevealedIds` props) | exact |
| `components/graph/graphElements.ts` (D-03 cluster parent) | transform | transform | itself (66L — add `parent: clusterId` to node `data`) | exact |
| `components/graph/graphStylesheet.ts` (PROB-32) | stylesheet | transform | itself (209L — add cluster parent styles + `.newly-revealed` + `.filtered-out`) | exact |
| `components/graph/GraphControls.tsx` (FEAT-06/09, D-04 focus) | component | UI | itself (98L — 44px icon-button stack; add Path/Share/Focus buttons) | exact |
| `components/graph/GraphLegend.tsx` (FEAT-11 cluster row) | component | UI | itself (203L — `NODE_TYPES` + `EDGE_TYPE_TO_FAMILY` exports) | exact |
| `components/graph/GraphCanvas.test.tsx` (D-05) | test | — | itself (:200 `toHaveLength(11)` → count-independent) | exact |
| `components/detail/DetailPanel.tsx` (FEAT-05/11) | component | request-response | itself (827L — header Export button, Backlinks tab, Properties dl) | exact |
| `components/detail/RevisionHistoryPanel.tsx` (+test) (FEAT-11.6) | component | request-response | itself (291L — `diffFields` value rendering) | exact |
| `components/layout/AppShell.tsx` (REBRAND h1 :46, topBar slots) | component | UI | itself (79L — `<h1 className="font-heading text-2xl">HD Graf Cehennemi</h1>`) | exact |
| `components/layout/HeaderNavAction.tsx` (FEAT-02/04 icon swap) | component | UI | itself (40L — icon/label/aria/active props) | exact |
| `components/chat/ChatSheet.tsx` (FEAT-10 mobile) | component | UI | itself (159L — sheet width classes) | exact |
| `hooks/useWatchProgress.ts` (+test) (PROB-31) | hook | request-response | itself (211L — no-op at :133/139; hydration effect :104-129) | exact |
| `hooks/useNotes.ts` (FEAT-07 raw notes) | hook | request-response | itself (82L — `fetchKeyRef` pattern; may already expose what FEAT-07 needs) | exact |
| `lib/byok.ts` (REBRAND key :9 + migration) | utility | file-I/O (localStorage) | itself (72L — `getStoredLLMSettings`/`saveLLMSettings`) | exact |
| `api/graph.ts` (FEAT-06 `findPath`) | client | request-response | itself (6L) + `api/progress.ts` | exact |
| `types/graph.ts` (FEAT-05/06 response shapes) | type | — | itself (79L) | exact |
| `App.tsx` (FEAT-02/03/04/08/09 routing) | composition root | request-response | itself (369L — `view` union `'graph'|'settings'` :71, topBar :248-270, GraphCanvas props :292-302) | exact |
| `frontend/index.html` (:12 title), root `index.html` (window-title), `frontend/package.json` (cytoscape-fcose@2.2.0), `vite.config.ts` (PROB-30 `envDir: '..'`) | config | — | themselves | exact |

## Pattern Assignments

### `backend/app/api/share.py` (controller, request-response) — FEAT-09

**Analog:** `backend/app/api/graph.py` (read path) + `backend/app/api/user_content.py` (route skeleton)

**Route skeleton + error mapping** (`api/user_content.py:27-62`):
```python
router = APIRouter(prefix="/api/series", tags=["user-content"])
DatabaseDependency = Annotated[Neo4jDatabase, Depends(get_database)]
Boundary = Annotated[int, Query(gt=0, description="Persisted positive spoiler boundary.", examples=[1])]

def _repository(database: Neo4jDatabase) -> UserContentRepository:
    return UserContentRepository(database)

def _not_found() -> Exception:
    return http_error(404, "resource_not_found", "Resource not found.")
```

**The SAME graph assembly path (D-09 — never fork a filter)** (`api/graph.py:87-113`):
```python
effective = visible_until_order
if user is not None:
    record = await progress_service.get(user["id"], series_id)
    if record is not None:
        requested_view = min(visible_until_order, record.view_as_of_order)
        effective = effective_view_order(requested_view, record.watched_through_order)

user_id = user["id"] if user is not None else None
cached = await get_cached_graph(series_id, effective, user_id)
if cached is not None:
    return GraphResponse.model_validate(cached)

result = await service.fetch_graph(series_id, effective,
    node_labels=VISIBLE_NODE_LABELS,
    user_relationship_types=USER_RELATIONSHIP_TYPES,
    effective_view_order=effective)
await set_cached_graph(series_id, effective, user_id, result.model_dump(mode="json"))
```
Share read route = resolve token → `visible_until_order = stored boundary`, `user_id=None`, call `GraphService.fetch_graph` the same way. Unauthenticated-but-token-gated: **no** `OptionalUserDependency`, just a `Depends` that resolves the token hash → `ShareTokenRecord | None` (401/404 via `http_error`).

**Share token create/read pattern** (RESEARCH.md Code Examples:319-333 + `repository/session.py:86-91`):
```python
def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

def _generate_token() -> str:
    return secrets.token_urlsafe(48)   # FEAT-09: token_urlsafe(32), return ONCE
```
Store `token_hash` + `series_id` + `visible_until_order` + `created_at` + `expires_at` (+ `revoked_at`) on a new `:ShareToken` node. Expiry/revoke read shape mirrors `Neo4jSessionRepository.get` (`session.py:217-246`): `WHERE s.revoked_at IS NULL AND s.expires_at > $now`.

### `backend/app/repository/share.py` (repository, CRUD) — FEAT-09

**Analog:** `backend/app/repository/session.py` — copy the Protocol + InMemory + Neo4j triple layout (`:54-99`, `:170-271`). Cypher labels must use `(:ShareToken)` — the `(:User)` label trap kills silently (skill). Sweep reuses the documented cleanup Cypher (`session.py:6-13`):
```cypher
MATCH (s:Session) WHERE s.expires_at < timestamp() OR s.revoked_at IS NOT NULL DETACH DELETE s
```
→ same shape for `:ShareToken` (expiry sweep mechanism is Claude's discretion, D-10).

### `backend/tests/test_google_verifier.py` (test, unit) — PROB-23

**Analog:** `backend/app/services/auth.py:52-93` `ProductionGoogleVerifier.verify`. Behavioral test: garbage token + `httpx.MockTransport`, assert `GoogleVerificationError`/`GoogleTransportError` mapping, never NameError. Config pitfall: `get_settings()` is `lru_cache`d (`core/config.py:1`) — monkeypatch attributes on the shared instance, never replace it (skill).

### `backend/app/repository/user_content.py` (repository, CRUD) — PROB-25/26 (+01/02)

**Analog:** itself. Two concrete change sites:

1. **`created_by` stamping (PROB-26, #50)** — add `created_by: $user_id` to the CREATE blocks. Note create shape (`user_content.py:145-150`):
```cypher
CREATE (note:UserNote {id: $id, series_id: $series_id,
  target_type: $target_type, target_id: $target_id, content: $content,
  visible_from_order: target.visible_from_order, origin: 'user',
  created_at: $created_at, updated_at: $updated_at})
CREATE (note)-[:REFERS_TO {id: $id + ':refers_to', series_id: $series_id,
  visible_from_order: target.visible_from_order, origin: 'user'}]->(target)
```
2. **Visibility derivation (PROB-25, #49)** — direct API stamps `episode.episode_order` (`user_content.py:176-180`, `CUSTOM_NODE_CREATE_QUERIES`):
```cypher
MATCH (episode:Episode {id: $episode_id, series_id: $series_id})
WHERE episode.episode_order IS NOT NULL AND episode.episode_order >= 1
CREATE (node:{node_type.value} {id: $id, series_id: $series_id, label: $label,
  episode_id: $episode_id, visible_from_order: episode.episode_order,
  origin: 'user', created_at: $created_at, updated_at: $updated_at})
```
ChangeSet apply stamps `current_progress` (`repository/change_set.py`) — extract ONE helper `max(episode order, current progress)` fail-closed per RESEARCH Responsibility Map (`RESEARCH.md:74-75`) and call from both. Ownership reads stay `OWNERSHIP_QUERY` (`user_content.py:276-279`).

### `backend/app/retrieval/pipeline.py` (service, transform) — PROB-24

**Analog:** itself. `assemble_context` ALREADY accepts `notes` (`pipeline.py:185`, `:219` — `("notes", _dedupe_by_id(_visible_at(notes, boundary)), _note_line)`). The gap is `_finalize` passing `notes=[]` (`pipeline.py:880`). Fix = add a `notes` accumulator bucket in `_accumulate` (`pipeline.py:818-857` — copy the `seen_*` dedupe shape per bucket, e.g. `seen_notes`) and pass `retrieved["notes"]` in `_finalize`. `get_user_notes` executor already exists (`tools.py:830`, registered in `_TOOL_EXECUTORS` at `:495`); it needs `user_id` threading if not already present.

### `backend/app/repository/session.py` + `services/auth.py` (PROB-03)

**Analog:** themselves. Id scheme `session:{user_id}:{int(now)}` (`session.py:209`) → `session:{uuid4()}`; add a sweep method (`MATCH (s:Session) WHERE s.expires_at < timestamp() OR s.revoked_at IS NOT NULL DETACH DELETE s`) + background task registration — the module docstring (`session.py:6-15`) already specifies it. Wire into `main.py` lifespan next to `init_rate_limiter()` (guarded on `redis_url`, skill 08-05).

### `backend/app/api/candidates.py` (PROB-12/33) — real persisted `revision_id`

**Analog:** itself. Approve/reject/edit currently PRE-COMPUTE `rev_id = f"revision:{hashlib.sha256(...)}"` (`candidates.py:206`, `:260`, `:319`) and return it instead of the id `RevisionRepository.log_revision` actually persisted (`:207-209`). ChangeSet revert (PROB-27) must keep BOTH ids — `apply_revision_id` + `revert_revision_id` — mirror `api/revisions.py`'s `_revert_work` (`revisions.py:133-271`) which already logs the REVERTED revision with `before`/`after` snapshots via `RevisionRepository.log_revision` (`:260-270`).

### `backend/app/spoiler/filter.py` (PROB-29) — series_id on SOURCES/EVIDENCE

**Analog:** itself. `SOURCES_QUERY`/`EVIDENCE_QUERY` MATCH on `(:Claim {series_id: $series_id})` but the bare `MATCH (source:Source)` / `MATCH (evidence:EvidenceFragment)` lack the series_id predicate (`filter.py:154`, `:183`) — add `{series_id: $series_id}` to those MATCHes. Keep the canonical visibility clause shape untouched (all 6 clauses at `:157-168`).

### `backend/app/graph/seed.py` (PROB-20/22 + ShareToken constraint)

**Analog:** itself. Add to the constraint/index block (`seed.py:134-228`), e.g.:
```python
await database.execute_query(
    "CREATE CONSTRAINT sharetoken_id_unique IF NOT EXISTS FOR (s:ShareToken) REQUIRE s.id IS UNIQUE"
)
await database.execute_query(
    "CREATE CONSTRAINT sharetoken_token_hash_unique IF NOT EXISTS FOR (s:ShareToken) REQUIRE s.token_hash IS UNIQUE"
)
await database.execute_query(
    "CREATE INDEX sharetoken_expires_at_idx IF NOT EXISTS FOR (s:ShareToken) ON (s.expires_at)"
)
```
⚠ `test_seed_idempotency.py` asserts an EXACT constraint-label set (RESEARCH Pitfall 2) — make the assertion additive/superset in the SAME plan that adds the constraint. Reseed path = `setup_database` (`seed.py:377`) via `graph/setup.py` CLI (`setup.py:9-24` — `database.open()` → `verify_connection()` → `setup_database` → `close()`); gate live AuraDB reseed behind the read-only `scripts/aura_graph_integrity.sh` audit.

### `backend/app/core/errors.py` + `api/auth.py` (PROB-09) — error-code casing

**Analog:** themselves. `ErrorDetail.code` regex is `^[a-z][a-z0-9_]*$` (`errors.py:28`) while routes emit uppercase `AUTH_*` (`api/auth.py:38-44`). RESEARCH Open Q2 recommendation: uppercase canonical codes (`AUTH_UNAUTHENTICATED`, `INVALID_REQUEST`, …), update the regex to `^[A-Z][A-Z0-9_]*$`, and move `client.ts` normalization + `test_openapi_contract.py` together in one plan. All new routes use `error_responses(404, 409, 422, 503)` + `http_error(...)` — never ad-hoc envelopes.

### `backend/app/api/graph.py` (FEAT-05 export + FEAT-06 path routes)

**Analog:** itself. FEAT-06 = thin route calling the allowlisted `find_path` executor (Pattern 3) with boundary from the existing resolution block (`api/graph.py:79-94`):
```python
async def find_path(database: Neo4jDatabase, *, source_entity_id: str, target_entity_id: str,
    max_hops: int, series_id: str, visible_until_order: int) -> dict[str, Any]:
    # tools.py:519-606 — BFS over CLAIMS_FOR_FRONTIER_QUERY; result {"found","path","edges","hops"}
```
FEAT-05 export = GET route rendering Markdown from the SAME filtered read path (`fetch_graph`/`spoiler.filter`), zero new deps (D-11). Route uses `error_responses(404, 422, 503)` + `OptionalUserDependency` exactly like the existing GET.

### Frontend `GraphCanvas.tsx` (PROB-32, D-03..D-06) + extracted modules

**Analog:** itself. The fcose swap rides the EXISTING imperative-layout path — `layoutOptionsFor` + try/catch registration (`GraphCanvas.tsx:33-87`):
```ts
let layoutName: 'cose-bilkent' | 'cose' = 'cose-bilkent'
try {
  cytoscape.use(coseBilkent)
} catch (error) { console.error(...); layoutName = 'cose' }

function layoutOptionsFor(name: 'cose-bilkent' | 'cose') {
  const common = { fit: true, padding: 48, nodeRepulsion: 8000,
    idealEdgeLength: 100, edgeElasticity: 0.45,
    animate: prefersReducedMotion ? false : ('end' as const) }
  ...
}
function runLayout(cy: cytoscape.Core) {
  if (typeof cy.layout !== 'function') return   // test-double guard — KEEP
  try { cy.layout(layoutOptionsFor(layoutName)).run() } catch ...
}
```
Extend the union to `'fcose'` per RESEARCH Code Example (`RESEARCH.md:290-316` — `quality:'default'`, `randomize:false`). **Extract** `layoutConfig.ts` (this block), `filterState.ts` (cache positions per `(seriesId, visibleUntilOrder)` — the `useGraph.ts:46` key string is the precedent), `focusReducer.ts` (the `.faded`/`.selected-dominant` logic at `:346-397`:
```ts
cy.elements().removeClass('selected-dominant faded edge-active')
focused.addClass('selected-dominant')
cy.elements().difference(focused).addClass('faded')
```
). New props are optional/nullable with defaults exactly like `focusedElementIds?`/`revealElementIds?` (`GraphCanvas.tsx:127-134`) so `GraphCanvas.test.tsx` keeps compiling. `readOnly` prop: hide FAB/edit affordances, keep pan/zoom/tap (FEAT-09). D-05: make `:200` `toHaveLength(11)` count-independent (RESEARCH Assumption A8 — keep the toy fixture, assert differently).

### `graphElements.ts` + `graphStylesheet.ts` (cluster parents, culling, filters)

**Analog:** themselves. `graphToElements` (`graphElements.ts:25-66`) maps node data `{id, label, nodeType, origin, imageUrl?}` — add `parent: clusterId` (subplot/cluster tag or `visible_from_order` band via the `episodes` prop). Stylesheet (`graphStylesheet.ts:24` `buildGraphStylesheet(prefersReducedMotion)`): add compound-parent style block, zoom-culling as a stylesheet function on `cy.zoom()`, `.filtered-out { display: none }`, `.newly-revealed` overlay (reuse `selected-dominant` overlay shape at `:114-121`: `overlay-color '#7C3AED'` + opacity + padding). Existing classes `node.hovered` `:126`, `edge.hovered, edge.edge-active` `:193`, `edge.faded` `:201` are the FEAT-06 `.on-path`/`.path-source`/`.path-target` and D-04 focus-mode foundations.

### `GraphControls.tsx` (FEAT-06/09 buttons, D-04 focus toggle)

**Analog:** itself. Copy the 44px icon-button + Tooltip stack verbatim (`GraphControls.tsx:39-96`) — `aria-label`, `flex h-11 w-11 ... bg-card text-muted-foreground shadow-sm ring-1 ring-border hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring`; `cy.fit(undefined, 48)` is the FEAT-01/06 framing call (`:36`). Props stay `{ cyRef, onReset }`-shaped — add `onPathMode`, `onShare`, `onFocusToggle` callbacks, not cy access.

### `lib/byok.ts` (REBRAND + FEAT-04 bookmarks/theme localStorage)

**Analog:** itself. Rename `BYOK_STORAGE_KEY = 'hdgraf:byok-llm-settings'` → `'spoilerless:byok-llm-settings'` (`byok.ts:9`) with read-compat migration in `getStoredLLMSettings` (`:16-35`): read old key if new absent; delete old key on next successful `saveLLMSettings` (`:41-49`). FEAT-04 bookmark/theme features copy this exact shape (try/catch parse + `Partial` field validation + `window.localStorage.setItem(KEY, JSON.stringify(...))`). `useWatchProgress.ts:33` `STORAGE_KEY = 'hdgraf.watchProgress'` is a SECOND localStorage key the rename sweep must check (sessionStorage, same bucket).

### `useWatchProgress.ts` (PROB-31)

**Analog:** itself. Silent no-ops at `:133` (`if (nextOrder === currentView) return`) and `:139-146` (view-only path — the `watched != null && nextOrder <= watched` branch must ALWAYS open the unlock dialog on forward / load view-only on backward, never swallow); mount hydration race is the effect at `:104-129` (mount-only `[]` deps — `viewAsOfOrder` can go stale; fix + regression test "locked-episode click with failing view-only POST still opens unlock dialog"). Wire-shape regression per RESEARCH Pitfall 4 — assert via transport-level fetch stub (pattern: `api/chat.test.ts` replaces `globalThis.fetch`), never `vi.mock('@/api/progress')`. Payload builder precedent: `api/progress.ts:36-53` (per-intent body, never both boundary fields).

### `api/client.ts` + `api/*.ts` (FEAT-09 share.ts / FEAT-05 export.ts / FEAT-06 findPath)

**Analog:** `api/graph.ts:1-6`:
```ts
export function getGraph(seriesId: string, visibleUntilOrder: number): Promise<GraphResponse> {
  return apiFetch(`/api/series/${seriesId}/graph?visible_until_order=${visibleUntilOrder}`)
}
```
New clients use `apiFetch` (`client.ts:38-61` — `credentials: 'include'`, `ApiError` normalization; 204 → `undefined`). `export.ts` GET must pass `responseType`-style handling OR fetch the `.md` via raw `fetch` (Blob download via `URL.createObjectURL` + `a[download]` — zero-dep, D-11).

### `App.tsx` (FEAT-02/03/04/08/09 — no router)

**Analog:** itself. State-driven navigation precedent (`App.tsx:71` `const [view, setView] = useState<'graph' | 'settings'>('graph')`, toggled by `HeaderNavAction` `:262-268`). FEAT-02 extends the union → `'graph' | 'timeline' | 'settings'`. FEAT-09 share route: match `window.location.pathname` against `/^\/share\/[A-Za-z0-9_-]+$/` at the `App()` root BEFORE the auth gate (`AppContent` `:343-359` — unauthenticated renders `LoginPage`; share branch renders `ShareView` instead). GraphCanvas wiring (`:292-302`) shows the prop-passing shape for `newlyRevealedIds` (FEAT-03: diff around `watchProgress.confirmedOrder`), `onSelect`, `episodes`. `handleSelectElement`/`handleOpenDetail` (`:294`) is the FEAT-01/07 claim-selection reuse hook.

### `AppShell.tsx` + `HeaderNavAction.tsx` (REBRAND, FEAT-02/04 topBar)

**Analog:** themselves. Wordmark at `AppShell.tsx:46` `<h1 className="font-heading text-2xl">HD Graf Cehennemi</h1>` → "Spoilerless" (text-only, no token changes). `topBar` slot (`:10`, `:47`) accepts ReactNode — FEAT-02/04/08 add triggers there; `HeaderNavAction` (`:16-40`) is the shared icon/aria/active control to extend for the Timeline/Dashboard/Command icons.

## Shared Patterns

### Auth & ownership (PROB-01/02/26 — apply to ALL mutation routes)
**Source:** `backend/app/api/deps.py:48-112`
```python
async def require_current_user(request: Request, service: AuthServiceDependency) -> dict[str, Any]:
    ...
    if user is None:
        raise http_error(401, AUTH_UNAUTHENTICATED, "Authentication required.")
    request.state.user = user
    return user
CurrentUserDependency = Annotated[dict[str, Any], Depends(require_current_user)]
# require_admin: user.get("role") != "admin" → 403 "forbidden"  (deps.py:95-109)
```
Direct user-content API routes (currently dependency-free at `api/user_content.py`) gain `user: CurrentUserDependency` and pass `user["id"]` into repo commands → `created_by` (PROB-26). Candidate/revision mutations already carry `_admin: RequireAdminDependency` (`api/candidates.py:179`, `:235`, `:290`) — keep.

### Rate limiting + cache invalidation (apply to every new write route)
**Source:** `backend/app/services/rate_limit.py:64-98` — `RateLimiter.__call__` as `Depends`; `content_write_rate_limiter` / `login_rate_limiter`. **Source:** `backend/app/cache/graph_cache.py::invalidate_series` — call AFTER the write transaction commits, never in `finally` (skill 08-05); already the house pattern at `api/user_content.py:147`, `:174`, `:189`, `:207`, `:218` and `api/candidates.py:218`.

### The ONE visibility filter (PROB-25/29/49 — NEVER fork)
**Source:** `backend/app/spoiler/filter.py:52-53` (+ every query in the file)
```cypher
node.visible_from_order IS NOT NULL
AND node.visible_from_order <= $visible_until_order
```
Boundary derivation: `effective_view_order` (`spoiler/policy.py`, used at `api/graph.py:92`). FEAT-09's share route, FEAT-05 export, FEAT-06 path route ALL reuse this path — a second looser copy is the exact bug class #49/#53 flags.

### Error envelope (all new routes)
**Source:** `backend/app/core/errors.py:92-125` — `http_error(status, code, message)` + `error_responses(404, 409, 422, 503)`; envelope `{"detail": {"code", "message"}}`. Frontend mirror: `client.ts:13-24` `ApiError`.

### Scratch-series + teardown test isolation (PROB-06/22 — apply to ALL new/refactored graph tests)
**Source:** `backend/tests/test_retrieval_tools.py:74-75` [VERIFIED] + skill:
```python
SCRATCH_SERIES = "series_scratch_retrieval"

@asynccontextmanager
async def scratch_series(database: Neo4jDatabase) -> AsyncIterator[str]:
    try:
        yield SCRATCH_SERIES
    finally:
        await database.execute_query("MATCH (n {series_id: $sid}) DETACH DELETE n", sid=SCRATCH_SERIES)
```
Teardown must ALSO delete `UserSeriesProgress` rows and `origin='candidate'` nodes (`MATCH (n) WHERE n.origin = 'candidate' DETACH DELETE n` — RESEARCH Pattern 1). Never touch `series_dexter`; never delete `ae8a41b7-db96-40e8-b6c2-2e3c69aedb11`. Zombie sweep = dry-run count first, then delete rows with no progress/chat/ownership ties.

### Zero-cost chat/LLM verification (all chat/pipeline tests)
**Source:** `backend/app/llm/provider.py:415` `FakeLLMProvider` (production source, never network); per-call-index refinement for mixed tool-call + cited-done scripts (`index = len(self.calls)`). `get_settings()` is `lru_cache`d — `monkeypatch.setattr(get_settings(), ...)`, never replace (skill).

### Wire-shape FE tests (PROB-23/#47 — apply to progress/share/export/changeSet tests)
**Source:** `frontend/src/api/chat.test.ts` — replace `globalThis.fetch` with a stub and assert the REQUEST BODY; NEVER `vi.mock('@/api/progress')` and assert the buggy payload (the #43/08-01 shipping-green class).

### REBRAND-01 sweep (D-12 — do FIRST, wave 0)
**Source:** RESEARCH Runtime State Inventory (`RESEARCH.md:240-252`) + Pitfall 8. Verified surface: `pyproject.toml` (`hdgraf-setup` console entry), `docker-compose.yml`, `render.yaml` (`name: hdgrafcehennemi-api`), `backend/app/main.py` `SERVICE_NAME` (→ breaks `test_graph_api.py:101` — update in the SAME plan), `frontend/src/lib/byok.ts:9` (localStorage key + migration), `AppShell.tsx:46` h1, `frontend/index.html:12` title, root `index.html` `window-title`/`GITHUB_REPOSITORY_URL`, `backend/scripts/smoke.sh`, `README.md`, `docs/*`, `backend/requirements.txt` (delete/regen). Gate: `git grep -il 'hdgrafcehennemi\|HD Graf Cehennemi'` → zero hits in tracked product/docs files (excluding `.planning/` history + PROBLEMS.md trail). Full import-root rename (`backend/` → `spoilerless/`) is the Open Q1 recommendation; metadata-only is the documented fallback.

### Frontend build/lint gates (every frontend plan)
`npm run build` (`tsc -b && vite build`) is the canonical typecheck — bare `tsc --noEmit` skips referenced projects (RESEARCH Pitfall 5; `options?.headers` fix pattern). Full frontend gate: `cd frontend && NODE_ENV=test CI=1 npm run test` + `npm run build` + `npm run lint` (PROB-08/09-06 must FIX stale-ref bugs — `fetchKeyRef.current` writes move out of render bodies into effects — not scope more rules to warn).

## No Analog Found

| File | Role | Data Flow | Reason / Fallback |
|---|---|---|---|
| `frontend/src/components/share/ShareView.tsx` | component (read-only shell) | request-response | No unauthenticated read-only shell exists (App.tsx gates everything behind auth). Analog = AppShell.tsx minimal header + GraphCanvas readOnly prop; RESEARCH/UI-SPEC contract is the spec. |
| `frontend/src/components/palette/CommandPalette.tsx` | component | event-driven UI | No ⌘K surface exists. Fallback: Dialog primitives + searchIndex.ts + HeaderNavAction trigger; UI-SPEC §10.10 is the contract. |
| `frontend/src/hooks/useHotkey.ts` | hook | event-driven | No global-keydown hook exists (GraphCanvas module-scope matchMedia at :29-31 is the closest capture pattern). Trivial; UI-SPEC Interaction Contract is the spec. |
| `frontend/src/lib/searchIndex.ts` | utility | transform | No client-side index exists (search was server-side SEARCH_ENTITIES_QUERY). Fallback: pure function over `GraphResponse` like graphElements.ts; zero-dep substring per FEATURE-RESEARCH. |

## Metadata

**Analog search scope:** `backend/app/{api,repository,services,retrieval,spoiler,core,graph,llm,cache}`, `backend/tests/`, `frontend/src/{components,hooks,api,lib,types}`, root config (`pyproject.toml`, `vite.config.ts`, `index.html`, `render.yaml`, `docker-compose.yml`, `.github/workflows/ci.yml`)
**Files scanned:** ~45 source files read directly (all line numbers verified this session)
**Pattern extraction date:** 2026-08-05
**Source docs:** 09-CONTEXT.md (D-01..D-14), 09-RESEARCH.md (§Architecture Patterns, Runtime State Inventory, Code Examples), 09-UI-SPEC.md (§Screen-by-Screen + Consolidated File Manifest), .planning/REQUIREMENTS.md (PROB-22..32), .planning/codebase/STRUCTURE.md, skill `hdgrafcehennemi`
