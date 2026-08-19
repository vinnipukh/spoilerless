# Cross-origin asset URLs & boundary invariants (prod split-origin)

## Bug class: backend-relative URLs consumed verbatim by frontend

Symptom: node portrait images (and any backend-served asset) render on
localhost, break on prod. Root cause: backend returns RELATIVE paths
(`image_url: "/api/static/characters/dexter_morgan.webp"` in
`data/dexter/seed/characters.json`); frontend consumes them verbatim.
Local dev works because the vite proxy forwards `/api` to the backend;
prod has split origins (frontend `spoilerless.net` on Vercel, backend
`api.spoilerless.net` on Render) so the relative URL resolves against the
wrong origin.

Probe recipe (proves it in seconds):
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://spoilerless.net/api/static/characters/dexter_morgan.webp        # 404/522 = broken (wrong origin)
curl -s -o /dev/null -w "%{http_code}\n" https://api.spoilerless.net/api/static/characters/dexter_morgan.webp   # 200 = image fine, wrong origin resolution
```

Fix pattern (landed as quick task 260813-gao):
- Export `apiUrl(path)` from `frontend/src/api/client.ts`; prefix ONLY
  `'/'`-leading paths with `VITE_API_BASE_URL`. Read the env at CALL time
  inside the function, never cache at module scope — vitest tests use
  `vi.stubEnv('VITE_API_BASE_URL', ...)` and module-scope caching makes
  them undriveable. Empty base → return path unchanged (local dev,
  existing tests stay green). Absolute http(s) URLs never prefixed.
- Apply at every consumption site (graphElements.ts Cytoscape `imageUrl`
  data key → graphStylesheet bg-image; DetailPanel.tsx `<img src>`).
- grep audit: `grep -rn "image_url\|imageUrl" frontend/src --include=*.ts --include=*.tsx | grep -v test` to find all sites.
- graphStylesheet comment: NO `background-image-crossorigin` is
  intentional — anonymous mode turns opaque-response failure into
  Cytoscape's broken-image glyph, worse than flat fill.

## D-05/PROB-04 invariant: client-chosen boundary must never widen the spoiler window

Every route that accepts `visible_until_order` must clamp to the
authenticated user's persisted progress (`progress_service.get` →
`min(requested, record.view_as_of_order)` → `effective_view_order(...)`),
and fail closed to `1` when NO progress record exists (fresh user's view
is the anonymous boundary). Missing clamp = CR-01 class bug (share-create
accepted order 60 from an order-1 user → public token served content far
beyond the sharer's window). Audit new boundary-accepting routes against
`api/graph.py` `_resolve_effective_boundary` as the reference pattern.
Regression-test with a fake progress dependency override
(`app.dependency_overrides[graph_api.get_progress_service]`) — never
write progress rows to the shared DB for this (test pollution).
