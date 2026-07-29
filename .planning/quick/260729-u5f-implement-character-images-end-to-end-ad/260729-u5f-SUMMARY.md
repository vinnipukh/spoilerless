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
- `data/dexter/seed/characters.json`: all 9 characters now carry manually
  verified `image_url`/`image_source_url`. No seed-loader code change was
  needed — `_upsert_nodes`'s `MERGE ... SET node += row` treats new JSON keys
  as an idempotent property update on reseed.
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

`WebFetch` (402), direct `curl` (Cloudflare JS challenge) were both blocked;
the Claude-in-Chrome extension was reconnected after the initial pass, and
all 9 mappings were fetched and verified live via the browser's own
`portable-infobox` DOM (og:image alone was unreliable — it sometimes points
at an unrelated season-promo card). Each direct image URL was confirmed to
actually load (`new Image()` load-event check, all 9 succeeded) before being
written to `data/dexter/seed/characters.json`:

| Character (seed label) | Fandom page | Note |
|---|---|---|
| Dexter Morgan | `/wiki/Dexter_Morgan` | |
| Debra Morgan | `/wiki/Debra_Morgan` | |
| Angel Batista | `/wiki/Angel_Batista` | |
| Maria LaGuerta | `/wiki/Maria_LaGuerta` | |
| James Doakes | `/wiki/James_Doakes` | |
| Rita Bennett | `/wiki/Rita_Morgan` | page titled by married name, not `Rita_Bennett` (that title 404s) |
| Paul Bennett | `/wiki/Paul_Bennett` | |
| Rudy Cooper | `/wiki/Brian_Moser` | page titled by true identity, not the alias `Rudy_Cooper` |
| Harry Morgan | `/wiki/Harry_Morgan` | |

All 9 seeded characters now have both fields populated. The
`test_graph_nodes_include_image_fields` test was updated to assert this
(9 Character nodes with populated fields; every non-Character node stays
null).

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
