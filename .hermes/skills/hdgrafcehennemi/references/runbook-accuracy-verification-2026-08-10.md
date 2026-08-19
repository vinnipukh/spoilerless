# RUNBOOK accuracy verification — 2026-08-10

Focused audit of `docs/RUNBOOK.md` against live source and bounded DB-free probes. Artifact: `.planning/tmp/verify-RUNBOOK.json` (50 checked, 36 passed, 14 failed).

## Durable operational facts

- **Health has only two live tuples:** success is HTTP 200 with `{status:"ok", database:"connected", service:"spoilerless-backend"}`; DB failure is HTTP 503 with `{status:"degraded", database:"unavailable", ...}`. Never document `status:"ok"` with an unavailable DB or say degraded means the app process itself is down.
- **Monitoring status must be cross-doc checked:** `docs/DEPLOYMENT.md` explicitly says the UptimeRobot monitor is planned/not configured. A runbook cannot present the same dashboard-only monitor as active without fresh external evidence.
- **Aura one-shot commands must include `NEO4J_DATABASE`:** `zombie_sweep.py` defaults it to `neo4j`; URI/user/password alone can select a wrong or nonexistent Aura database.
- **Startup schema-check scope is narrow:** `graph/setup.py::_check_visibility_schema` validates `visible_from_order` on `STORY_LABELS`; `Episode` is excluded and there is no check for `synopsis_visible_from_order` or `image_visible_from_order`.
- **Setup is mutating and incomplete as rollback:** `python -m spoilerless.app.graph.setup` has no dry-run CLI. It MERGEs canonical seed rows but does not remove arbitrary extra nodes, so it cannot be called the exclusive recovery for every bad reseed/pollution class. Pair it with a real non-mutating preflight if docs require dry-run + sign-off.
- **Redis prefixes are not product-name based:** graph cache keys are `graph:{series_id}:{boundary}:{user-or-anon}` and invalidation scans `graph:{series_id}:*`; rate-limit buckets are `hdgraf:rate_limit:*`. Flushing `spoilerless:*` clears neither.
- **Zombie-sweep tie safety is incomplete:** current queries guard `HAS_PROGRESS`, `HAS_SESSION`, `CREATED`, and `REFERS_TO`, but live ownership edges also include `HAS_CHAT_SESSION`, `PROPOSED_CHANGE_SET`, and `CREATED_SHARE`. Therefore `DETACH DELETE` can remove a user with retained chat/change-set/share data and orphan those records. Do not describe the script as deleting only truly tie-less users until all ownership relations are covered.
- **SSE codes are payloads, not frontend-console logs:** `api/chat.py` emits `LLM_PROVIDER_UNAVAILABLE` / `LLM_STREAM_FAILED` in `event:error` data. `ChatPanel` classifies them into UI states; it does not console-log them. The server logger messages also do not include those exact code strings, so a grep recipe using only the code names misses the logs.

## Audit pattern

For operational docs, split each line into independently checkable claims: command existence, complete env set, default database selection, safety gate, mutation scope, key prefix, health body/status pairing, and dashboard provisioning. Cross-check companion deployment docs because they often hold explicit `<!-- VERIFY: -->` state that contradicts an older runbook.
