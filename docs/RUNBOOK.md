# Runbook — incident detection, diagnosis, rollback (carry-over 09-08)

Executable by a future operator. No dashboards platform wiring — this is the
procedure, with the exact live-DB counts that distinguish failure classes.

## 1. Incident detection

- UptimeRobot monitor `https://api.spoilerless.net/health` alerts on any
  non-2xx (external monitor, phase 8).
- `/health` reports `{status, database, service}` — `database:
  "unavailable"` with `status: "ok"` means degraded startup (app up, graph
  down). `status: "degraded"` means the app itself is failing.
- Frontend console: chat stream errors emit `LLM_STREAM_FAILED`,
  `LLM_PROVIDER_UNAVAILABLE` events (09-06) — grep structured logs for the
  event name + exception class.

## 2. Diagnosis ladder

Run from the repo root with the live AuraDB env (root `.env`, never commit
it). Override per-run; do not edit `.env`:

```bash
unset PYTHONPATH
NEO4J_URI=neo4j+s://... NEO4J_USERNAME=... NEO4J_PASSWORD=... \
  uv run --project spoilerless python -m spoilerless.scripts.zombie_sweep --dry-run
```

| Symptom | Check | Counts that mean "this class" |
|---|---|---|
| Chat dead / streaming hangs | Sessions + chat messages | `:Session` rows expired ≫ live; orphaned `:ChatMessage` without owner |
| Graph wrong at boundary N | Seed integrity audit | `visible_from_order IS NULL` on seeded nodes; missing `synopsis_visible_from_order` on `:Episode` (01N52 storm class — the 09-08 startup schema check catches this at setup) |
| Slow login / 401 storms | Zombie users | Thousands of `:AppUser` with no ties (PROB-22/#46: ~3,855 on Aura) |
| LLM 429s | Redis rate limiter | `REDIS_URL` unset on Render (fail-open = unthrottled, not a crash) |

Structured-log grep points (Render logs):

```bash
grep -E "LLM_STREAM_FAILED|LLM_PROVIDER_UNAVAILABLE|Exception|ERROR" <log>
```

## 3. Rollback procedure

1. **Backend (Render):** redeploy the previous deploy (Render dashboard →
   service → Deploys → "Redeploy" on last known-good).
2. **Frontend (Vercel):** Production → Instant Rollback to the previous
   deployment.
3. **Graph:** the graph is the source of truth; a bad reseed is recoverable
   only by re-running `uv run --project spoilerless python -m
   spoilerless.app.graph.setup` (MERGE-based, preserves user content) —
   gated behind dry-run + operator sign-off (plan 09-18).
4. **Cache (Upstash Redis):** flush `spoilerless:*` keys via the Upstash
   console if a bad write path cached stale graph responses (09-06 write-path
   invalidation should prevent this; flush is the escape hatch).

## 4. On-call contact flow

1. Operator (repo owner) — GitHub notifications + Render/Vercel dashboards.
2. If operator unreachable: leave the previous deploy live, do NOT trigger
   the destructive reseed path without sign-off.
3. Record the incident in `docs/PROBLEMS.md` (canonical ledger) with the
   counts from §2 before fixing — every entry needs evidence.

## 5. Zombie sweep (PROB-22/#46)

```bash
# Dry-run FIRST (mandatory):
uv run --project spoilerless python -m spoilerless.scripts.zombie_sweep --dry-run
# Review counts, then:
uv run --project spoilerless python -m spoilerless.scripts.zombie_sweep --execute
```

HARD rules baked into the script: never deletes the protected dev user
(`ae8a41b7-db96-40e8-b6c2-2e3c69aedb11`); deletes only tie-less `:AppUser`
rows and expired/revoked/orphaned `:Session` nodes.
