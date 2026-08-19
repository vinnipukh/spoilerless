# Eighteenth pass: deploy-first debugging + self-hosted portraits (08-12)

## "It still doesn't work" = check deployment state FIRST
Three fixes (visitor spoiler modal, launch auto-refresh, portraits) were
verified locally — 337 vitest, contract tests, clean build — yet the user
still saw old behavior. Root cause: **53 unpushed commits**. Vercel/Render
auto-deploy from `main`; nothing had been pushed, so prod never changed.

Order of checks when the user reports a deployed fix "still broken":
1. `git rev-list --count origin/main..HEAD` — unpushed count is suspect #1.
2. Prod bundle: `curl -s https://app.spoilerless.net/ | grep -o 'src="[^"]*\.js"'`,
   fetch that asset, `grep -c "<unique string literal>"`. String literals
   survive minification — e.g. visitor-modal copy "may contain spoilers",
   button label "View episode" (both absent pre-push, present post-push).
3. Prod API: `curl -s -o /dev/null -w "%{http_code} %{content_type}"` on a new
   endpoint (404 JSON = backend mount not deployed); `/health` `service` field
   = build marker.
4. Only then touch code. Do NOT iterate on the implementation while the
   deployed artifact is stale — that is how a session burns hours re-fixing
   code that was already correct.

PITFALL: shell quote-strip `${bundle#src=\"}` leaves a trailing `"` in the
URL → curl fetches a 404 path → grep silently returns 0 → FALSE NEGATIVE
("fix not deployed" verdict on a deployed fix). Strip both quotes
(`tr -d '"'`) or paste the asset name literally.

Post-push polling (verified 08-12): push `ef91fee..0ff3829` → new bundle
hash in index.html by ~30s (try 2), Render static mount 200 by ~1 min
(try 4). Poll loop: `[ "$static" = "200" ] && [ "$has" = "1" ] && break`.

## Self-hosted character portraits (67ae4de, PROBLEMS #28 contract)
- #28 contract: images MUST be self-hosted — external CDN (Fandom
  static.wikia.nocookie.net) forever forbidden. Graph contract test
  (test_graph_api.py `test_graph_nodes_include_image_fields`) asserts
  `image_url` is None OR startswith `/api/static/`.
- Download (Fandom): needs BOTH desktop UA
  `-A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"` AND referer
  `-e https://dexter.fandom.com/`. Bare UA → HTTP 200 with 0 bytes
  (curl exit 23 write error).
- Fandom serves **WebP despite .jpg URLs**: files start RIFF (52 49 46 46),
  not JPEG magic. Rename to `.webp` so StaticFiles serves `image/webp`.
  Verify with a magic-byte check, not the extension.
- Serve under `/api/static`: `app.mount("/api/static", StaticFiles(directory=Path(__file__).parent / "static"))`.
  The `/api` prefix reuses the SPA's existing `/api` proxy (Vite dev) and
  Vercel `/api` rewrite, so RELATIVE urls work on any origin; also passes
  CSP `img-src 'self'`.
- Seed stores the relative url (`/api/static/characters/<id>.webp`). The
  self-healing upsert (4c4e77a) deletes keys absent from seed rows — seed
  JSON is the single source of truth; re-seeding strips stray keys.
- **AuraDB (prod) needs a RESEED for `image_url` values**: static files
  serve 200 but graph API returns null image_url until the Aura reseed
  runs (09-18-gated operator step). Local docker reseed only proves the
  code path.
- Keep `scripts/add_portraits.py` as the re-add recipe (id→URL map +
  strip-stray-keys).

## GUI automation blind spots (Windows, this machine)
- Chrome page content is absent from the AX tree when the window is
  backgrounded (only window-chrome elements listed; window_title empty) —
  captures look "empty" for a canvas app.
- No vision provider configured → screenshots cannot be analyzed
  ("No LLM provider configured for task=vision").
- Typed-browser rung refused: `browser_requires_setup` (no owned DevTools
  endpoint; `cua_browser_prepare` needs approval and standard mode fails
  closed without a certified host).
- Working fallback: verify via terminal artifacts (bundle grep, HTTP
  probes, uvicorn/vite logs) and reload the user's tab with a background
  click on the Reload element (works on Chromium); tell the user to F5 if
  it doesn't land. Don't burn time on GUI when the evidence lives in HTTP.
