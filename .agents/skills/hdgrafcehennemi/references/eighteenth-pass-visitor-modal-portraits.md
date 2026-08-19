# Visitor spoiler modal + self-hosted portraits (EIGHTEENTH PASS, 08-12)

## Visitor (persist:false) forward navigation MUST warn (d150d1e)
History: quick task 260805-te3 made visitors read-only (`persist: false`,
never POSTs) and skipped the unlock modal entirely ("no POST, no unlock
modal"). That behavior shipped to prod for the FIRST time with the 08-12
push → user: "I can navigate between episodes without any notification
telling me I can see spoilers."

Rules now (useWatchProgress.ts):
- Visitor `requestChange`: forward move ABOVE current view → set
  `pendingChange` (modal opens, visitor copy). Same-order / backward → silent
  local view move. First interaction (currentView null: entry seed, series
  switch) → silent — no boundary exists yet to spoil, and the entry seed must
  not pop a dialog.
- Visitor `confirmChange`: applies
  `{seriesId, watchedThroughOrder: nextOrder, viewAsOfOrder: nextOrder,
  pendingChange: null}` locally, NEVER POSTs.
- `ConfirmAdvanceModal` `visitor` prop: title "View S01E0N?", body
  "Content beyond your current progress may contain spoilers. Your progress
  isn't saved in visitor mode. Continue?", confirm "View episode". Auth copy
  untouched (locked by 02-UI-SPEC Copywriting Contract).
- Tests: 5 hook-level visitor cases + App-level integration (visitor click
  above boundary → modal before any graph fetch; confirm → fetch
  `visible_until_order=N`).

**Lesson: prod behavior changes ride in with unrelated deploys.** The
08-05 visitor design reached prod 08-12 via an unrelated push. When the user
reports a regression right after a deploy, diff what SHIPPED vs local HEAD
before blaming local changes — then fix the UX gap regardless of who caused
it.

## Self-hosted character portraits (PROBLEMS #28 contract) (67ae4de)
- Contract: images self-hosted ONLY, never external CDN
  (static.wikia.nocookie.net / fandom). Graph API test enforces:
  `image_url` is null OR startswith `/api/static/`; absolute http(s) URLs
  fail the suite. Re-adding hotlinks = test failure by design.
- Fandom download quirks: needs
  `curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" -e "https://dexter.fandom.com/"`
  (Referer required). Files come back as **WEBP (RIFF magic `52 49 46 46`)**
  even though the URL ends `.jpg` — rename to `.webp` so StaticFiles serves
  `image/webp`. `curl -o /dev/null -w "%{size_download}"` reports 0B / exit
  23 on MSYS for downloads that actually succeed — verify with a real file +
  size instead.
- Serving: `app.mount("/api/static", StaticFiles(directory=<app>/static),
  name="static")` in main.py. The `/api` prefix reuses the SPA's existing
  /api path (Vite dev proxy, Vercel rewrite) and relative URLs pass CSP
  `img-src 'self'`.
- Seed: characters.json carries RELATIVE `image_url`
  (`/api/static/characters/<id>.webp`). The self-healing upsert (4c4e77a)
  **DELETES node keys absent from the seed row** — image_url MUST live in the
  seed JSON or reseed wipes it from live DBs.
- Reseed command: `uv run spoilerless-setup` fails ("program not found");
  use `.venv/Scripts/python.exe -m spoilerless.app.graph.setup` with
  `source scripts/env-local.sh` + `aura_uri/aura_username/aura_database`
  exported + `unset PYTHONPATH`.
- AuraDB (prod) needs its own reseed (09-18 gate) before prod carries URLs.
- One-off seed mutation: use a `scripts/` python file (json load → patch →
  dump) — never sed/re.sub in heredocs (MSYS backreference/SOH mangling).

## Character id → portrait filename map (Dexter seed)
dexter:character:dexter_morgan → dexter_morgan.webp
dexter:character:debra_morgan → debra_morgan.webp
dexter:character:angel_batista → angel_batista.webp
dexter:character:maria_laguerta → maria_laguerta.webp
dexter:character:james_doakes → james_doakes.webp
dexter:character:rita_bennett → rita_bennett.webp
