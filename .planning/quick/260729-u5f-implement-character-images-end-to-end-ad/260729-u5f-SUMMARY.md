---
status: complete
task: "Implement character images end-to-end"
date: 2026-07-29
commit: "feat: add optional character portrait images to graph and detail panel"
---

# Quick Task Summary: Character images end-to-end

## Changes

- `backend/app/domain/graph.py`: `GraphNode` gained optional `image_url` /
  `image_source_url` (default `None`).
- `backend/app/spoiler/filter.py`: `NODES_QUERY` now returns
  `image_url`/`image_source_url` for every node type (non-Character nodes
  read back `null` since the property is never set on them).
- No seed-loader or `data/dexter/seed/characters.json` change was required —
  `_upsert_nodes`'s `MERGE ... SET node += row` already treats missing keys
  as idempotent no-ops, and adding image fields later is a matter of adding
  keys to that JSON and re-running the seed.
- `frontend/src/types/graph.ts`: `GraphNode` mirrors the two new fields.
- `frontend/src/components/graph/graphElements.ts`: sets a Cytoscape
  `imageUrl` data key only for `Character` nodes with a non-null `image_url`
  (key omitted otherwise, not nulled, so the stylesheet selector can't
  false-match).
- `frontend/src/components/graph/graphStylesheet.ts`: added
  `node[nodeType = "Character"][imageUrl]` → circular `background-image`
  (`background-fit: cover`, `background-clip: node`); Cytoscape draws to
  canvas so a failed/blocked image load just falls back to the existing flat
  fill, never a broken-image box.
- `frontend/src/components/detail/DetailPanel.tsx`: new `CharacterPortrait`
  subcomponent — `<img>` with `onError` fallback to an initials avatar,
  wrapped in `<a target="_blank" rel="noopener noreferrer">` when
  `image_source_url` exists; rendered in the Sheet header only for Character
  selections.
- Test fixtures/tests updated: `graphResponse.ts` (all nodes carry the two
  new fields; `char_dexter_morgan` seeded with example values to exercise the
  "has image" path), new `graphElements.test.ts`, and new `DetailPanel.test.tsx`
  cases (portrait+link, initials fallback, load-failure fallback, no-avatar
  for non-Character selections).

## Character-to-image mappings

None seeded. `WebFetch` returned HTTP 402, no Chrome extension was connected,
and a direct `curl` to `dexter.fandom.com` was blocked by a Cloudflare JS
challenge — there was no way to verify a real, direct image URL this session.
Per the task's explicit "do not invent mappings when uncertain" instruction,
all 9 Dexter S01E01–03 characters (`dexter_morgan`, `debra_morgan`,
`angel_batista`, `maria_laguerta`, `james_doakes`, `rita_bennett`,
`paul_bennett`, `rudy_cooper`, `harry_morgan`) are left with
`image_url`/`image_source_url` both `null`. The plumbing is fully wired end
to end; adding real mappings later is a JSON edit + reseed.

## Verification Evidence

- Backend: `uv run pytest backend/tests/ -q` → 116 passed (includes 3 new
  image-field tests: 2 model-level, 1 live-DB payload check).
- Frontend: `npm run test -- --run` → 32 passed (25 pre-existing + 7 new).
- Frontend: `npx tsc --noEmit -p tsconfig.app.json` → clean, no `any` used.
- Frontend: `npm run build` → succeeds.
- Manual browser verification (opening the app, clicking a seeded-image
  Character node, confirming the graph portrait and detail-panel portrait
  render and the source link opens in a new tab) was **not** performed this
  session — no character currently has a real seeded image, so there is
  nothing to visually verify yet beyond the fallback paths already covered
  by automated tests.

## Commit Info

Atomic commit message: `feat: add optional character portrait images to graph and detail panel`. Exact SHA reported by Git after commit creation.
