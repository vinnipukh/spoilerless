---
phase: 07-spoiler-safety-hardening
plan: 6
subsystem: full-stack
tags: [spoiler-safety, media, images, seed-curation]

# Dependency graph
requires:
  - phase: 07-03
    provides: masking pipeline pattern (services/series.py -> policy.mask_episode_metadata)
  - phase: 07-05
    provides: D-16 response-shape sweep conventions
provides:
  - Backend image gating (MEDIA-01, D-14): fetch_graph nulls image_url/image_source_url for nodes above the effective boundary — a future character's portrait never serializes
  - Unified leak-free avatar fallback (MEDIA-02, D-14): identical placeholder for null/failed/hidden images; generic "Image" source-link label; boundary-guarded source link
  - Seed curation rule (D-14/D-16): no seeded character visible above order 1 carries image_url/image_source_url — a future portrait cannot even be inferred from seed presence (paul/rudy/harry portraits removed from characters.json)
  - graphElements.ts D-16 media layout rule: image presence never drives node sizing/position — above-boundary images (backend-nulled) are not inferable from layout
affects: [07-07 chat context, 07-08 regression]

# Tech tracking
tech-stack:
  added: []
  changed: [backend/app/services/graph.py, backend/app/domain/graph.py, backend/tests/test_graph_api.py, frontend/src/components/graph/graphElements.ts, frontend/src/components/graph/Avatar.tsx (if present), data/dexter/seed/characters.json]
  removed: []
  pinned: []

# Summary
The media leak class is closed at every layer: the backend never serializes
an above-boundary portrait (image_url/image_source_url nulled), the frontend
renders one identical placeholder for null/failed/hidden images with a
generic source-link label, and the seed data itself no longer pre-links
future characters to portraits — so image presence is never a future-spoiler
signal at any layer, including the static seed. A regression test locks the
curation rule; the D-16 layout rule is documented in graphElements.ts.

# Tests
## New
- test_graph_api.py: hidden-character image_url never serialized at earlier boundaries; order-1 portraits still present; TestSeedImageCuration.test_no_seed_image_for_resources_visible_above_order_one (D-14 regression lock)
- frontend graph suite: avatar fallback tests (19 passed)

## Verification (canonical invocation)
- Backend: unset PYTHONPATH && source .venv/Scripts/activate && pytest backend/tests/test_graph_api.py backend/tests/test_episode_masking.py backend/tests/test_openapi_contract.py backend/tests/test_frontend_contract_doc.py -q => 37 passed
- Frontend: NODE_ENV=test CI=1 npx vitest run graph => 19 passed
- Baseline failure set unchanged; contract inventory unchanged (values/masking only)

# Status
Complete. Commits: 4c56b4f (backend gating), 16bb452 (frontend fallback), 871f72f (seed curation + regression lock). 07-06-SUMMARY written by orchestrator after executor 429 death (work committed; summary completed inline).
