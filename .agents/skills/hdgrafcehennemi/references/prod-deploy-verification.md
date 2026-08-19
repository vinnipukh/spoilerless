# Prod deploy verification (spoilerless.net / app.spoilerless.net / Render)

Validated 2026-08-13 (260813-gao push). How to verify a pushed frontend fix actually shipped, and the origin traps that produce false conclusions.

## Origin map (three distinct hosts, do not mix them)
- `spoilerless.net` — Cloudflare-fronted. `GET /` → **301** → `app.spoilerless.net`. When Cloudflare→Vercel origin connection fails, EVERY request through this host returns **HTTP 522** with a 16-byte body `error code: 522`. Probes through it are unreliable.
- `app.spoilerless.net` — direct Vercel (response header `Server: Vercel`). This is the origin browsers actually load. Probe THIS one.
- `api.spoilerless.net` — Render backend (`Server: Render`), `/health` → `service: spoilerless-backend` = new build, `hdgrafcehennemi-backend` = stale.

Check `Server:` header to learn which origin answered before trusting any probe.

## The 522 trap (false "stale bundle" conclusion)
`curl -sL https://spoilerless.net/assets/index-X.js` follows the 301 to app.spoilerless.net ONLY if -L is used on the FINAL url; fetching `https://spoilerless.net/assets/...` directly returns the 522 error body — 16 bytes, not JS. Grepping it for your marker yields 0 hits → you conclude "deploy not live" when you never looked at the real bundle. Always fetch the asset from `app.spoilerless.net`.

## Deploy-liveness check (bundle hash + marker grep)
```bash
HASH=$(curl -s --max-time 20 "https://app.spoilerless.net/" | grep -oE '/assets/index-[^"]+\.js' | head -1 | sed 's|/assets/index-||;s|\.js||')
curl -s --max-time 30 "https://app.spoilerless.net/assets/index-${HASH}.js" | grep -c "<YOUR-MARKER>"
```
- Hash change = new deploy shipped; marker present = fix reached the bundle.
- Old bundle stays live until Vercel finishes; 10+ min with unchanged hash after push → deploy not triggered or build failed → **Vercel dashboard is operator-touch** (no VERCEL_TOKEN in repo; git status API 404s on private repos without auth).
- Render backend deploys fast (auto-deploy on main push); Vercel can lag 5-40 min or silently skip.

## VITE_API_BASE_URL build-env fact (260813-gao)
- Vercel project env `VITE_API_BASE_URL` was **UNSET** at last successful build: old bundle contained zero occurrences of `api.spoilerless.net` (grep-verified). Relative `/api` calls work in prod anyway via a dashboard-level Vercel rewrite (no `vercel.json` in repo; `app.spoilerless.net/api/series` → 200).
- Consequence: the `apiUrl()` prefixing fix is **inert until `VITE_API_BASE_URL=https://api.spoilerless.net` is set in the Vercel project env** and the app redeployed. New bundle only contains the `api.spoilerless.net/api/static` marker when the env is set. Operator-touch item; flag it in the completion report.

## Polling pattern
Background poll with `notify_on_complete=true`: loop `HASH=$(fetch index); grep bundle; sleep 60` up to N iterations, exit 0 on marker found. Report honestly on timeout — do not re-run foreground loops to burn the 600s cap.
