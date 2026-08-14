# S8 — Abuse / DoS / Resource-Exhaustion / Denial-of-Wallet Audit

**Auditor:** S8 (abuse/DoS subagent) · **Date:** 2026-08-15 · **Scope:** spoilerless backend (FastAPI + Neo4j + Upstash Redis + LLM providers) · **Method:** static analysis + worst-case arithmetic. No live traffic, no load tests, no DB access.

**Deployment facts used throughout:**
- `render.yaml` start command: `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT` — **single process, single worker** (no `--workers`), free tier.
- Rate limiting is Redis-backed and **fail-open by design** (`services/rate_limit.py`); Redis empty/unreachable ⇒ no limits.
- Chat LLM: server-side key stored in `:AppSetting` (admin-set) used when no BYOK headers; BYOK headers (`X-LLM-Api-Key` etc.) shift cost to the attacker's own key — BYOK is the one strong wallet defense.
- Per turn: up to `llm_max_tool_rounds` (4) tool-round provider calls + 1 final call = **up to 5 provider calls/turn** (`retrieval/pipeline.py:780-878, 1034-1044`). No provider retry loop (good).
- Pricing reference (verify at audit time): Gemini 2.5 Flash ≈ $0.30/1M input tokens, $2.50/1M output tokens. All $ figures scale linearly with actual model price.

---

## SEC-DOS-001 — Rate limiting is fail-open: any Redis outage/absence silently disables every limit
| Field | Value |
|---|---|
| Severity / Confidence | **High / High** |
| Component | `services/rate_limit.py:86-105` (`__call__` swallows all exceptions), `:116-148` (`init_rate_limiter` degrades), `main.py:121-125` (guarded on non-empty `REDIS_URL`), `config.py:79-87` (`redis_url` default empty) |
| Entry point | Any rate-limited route (login, chat-send, content-write) |
| Data flow | Request → `RateLimiter.__call__` → `limiter.try_acquire_async` → exception/None ⇒ pass |
| Vulnerability | Every failure mode of Redis (outage, latency, eviction, misconfig, empty env) converts the limiter into a no-op **without any alert or degradation signal**. Production on Render free tier + external Upstash: an Upstash blip or a failed `RedisBucket.init` at startup leaves the app permanently unthrottled for the lifetime of the process (no re-init retry loop). |
| Attack scenario | Attacker triggers or waits for a Redis hiccup (Upstash free-tier throttling, network blip), then runs chat at full speed: per-user 20/min cap gone ⇒ 1 account burns server-key LLM tokens at wire rate. |
| Impact | Denial-of-wallet: with no rate limit, a single account sustains ~2-5 turns/s (each up to 5 LLM calls) ⇒ ≈$3-15/hr per account at Gemini 2.5 Flash rates, unbounded. Plus Neo4j/Redis write amplification. |
| Reproduction (safe math) | Turn off `REDIS_URL` (default local dev) or point it at a dead host; observe 429s disappear (code reading: exception path returns without calling `rate_limit_callback`). No flood needed to prove the code path. |
| Existing defenses | None — degrade-not-fail is explicit design (PROB-23). |
| Recommended fix | Fail-closed with expiry: cache limiters locally and treat *unreachable Redis* as 429 for write/paid routes (or a short global in-process quota); add a startup/periodic re-init; alert when `_limiter is None` in production; surface limiter state in `/health`. |
| Verification | Unit test: monkeypatch `try_acquire_async` to raise ⇒ expect 429 (fail closed), not 200. Integration: kill Redis, confirm chat-send still throttled. |

## SEC-DOS-002 — LLM cost amplification: account farming defeats per-user limits (open signup × 20 msg/min × 5 LLM calls)
| Field | Value |
|---|---|
| Severity / Confidence | **Critical / High** |
| Component | `config.py:60-67` (`allowed_emails` default empty = any verified Google account), `api/auth.py:92-174` (login creates user), `api/chat.py:147-165,178-263` (chat-send 20/min/user only), `services/chat.py:50` (concurrency 1/user), `retrieval/pipeline.py:780-878` (4 tool rounds + final call) |
| Entry point | `POST /api/series/{id}/chat/sessions/{sid}/messages` (+ `/stream`) with a server-side-key session |
| Data flow | question (≤4000 chars) → history load (ALL session messages) → 4 tool rounds (messages list grows: each tool result replayed up to 4000 chars) → final call with ≤12000-char context + ≤40 history items + 827-line system prompt + 12 tool schemas |
| Vulnerability | (a) Rate limit is per **user id**; accounts are free (Google OAuth, allowlist empty by default), session TTL 7 days ⇒ farm N accounts to multiply throughput by N. (b) Per-turn input tokens grow across rounds: worst case ≈ 40-60k input + up to 4k output tokens per turn (5 calls × 800 max output). (c) `llm_timeout_seconds=60` ⇒ one turn can pin a worker for up to 5×60s=300s. |
| Attack scenario | 10 burner Google accounts, log in once each (10 logins/5min limit per IP is irrelevant over hours), then each runs 20 msgs/min continuously. 200 turns/min total. |
| Impact | Cost: ≈$0.02-0.03/turn (Gemini 2.5 Flash: ~40k in ≈ $0.012, ~4k out ≈ $0.010). 20/min/account × 10 accounts = 1,200 turns/hr ≈ **$25-36/hr ≈ $600-860/day per 10-account farm**. 100 accounts ⇒ ~$6-8.6k/day. Even the cheapest path (1 call/turn, no tools) ≈ $0.005/turn ⇒ $6/hr/account-farm. Also CPU: 10 concurrent turns each holding 5 sequential provider calls + Neo4j BFS queries saturate the single uvicorn worker. |
| Reproduction (safe math) | 40k input + 4k output per turn is the documented maximum (tool-round cap 4, output cap 800×5, context cap 12k chars, replay cap 4k chars/result); multiply by 20/min × N accounts. No live calls needed. |
| Existing defenses | BYOK headers (cost shifts to attacker's key — but attacker simply omits them), per-user 20/min (defeated by accounts), per-user concurrency=1 (defeated by accounts), tool-round/context/output caps (bounded per turn, not per attacker). |
| Recommended fix | Email allowlist in production (config already supports it); per-IP+per-user chat limits; daily token budget per user (Redis counters on input/output tokens per turn); require admin approval for server-key chat, or make BYOK mandatory; global concurrent-turn semaphore + per-IP concurrency cap; cheaper fallback model when no tool rounds needed. |
| Verification | Unit test: N fake users × 20 requests ⇒ assert global token-budget counter trips; assert 429 on IP once per-IP cap added. |

## SEC-DOS-003 — Per-IP rate limits are proxy-collapsed (or spoofable): login limit becomes site-global; XFF not trusted
| Field | Value |
|---|---|
| Severity / Confidence | **High / Medium** |
| Component | `services/rate_limit.py:41-50` (`request.client.host`), `render.yaml:10` (uvicorn default `proxy_headers=True, forwarded_allow_ips="127.0.0.1"`), `.env.example` (no `FORWARDED_ALLOW_IPS`) |
| Entry point | `POST /api/auth/google` (login 10/5min), any future anonymous rate-limited route |
| Data flow | Client → Render proxy (adds X-Forwarded-For) → uvicorn (ignores XFF unless proxy IP trusted) ⇒ `client.host` = Render proxy IP for every user |
| Vulnerability | With defaults, every client shares ONE rate-limit bucket. (a) **Login DoS**: 10 logins/5min total for the whole site — attacker (or any misbehaving client) exhausts it for all legitimate users; (b) if ops ever set `FORWARDED_ALLOW_IPS=*` (common Render guidance), attackers spoof arbitrary `X-Forwarded-For` to bypass per-IP limits entirely. |
| Attack scenario | Script sends 10 rapid `/api/auth/google` POSTs ⇒ all logins site-wide 429 for 5 minutes. Repeat every 5 min = permanent login outage. |
| Impact | Availability: total login outage; no wallet impact. |
| Reproduction (safe reasoning) | Render's proxy IP ∉ {127.0.0.1} ⇒ uvicorn's proxy-headers trust list never matches ⇒ XFF ignored. Static reasoning from uvicorn defaults + render.yaml; verify with `request.client.host` logging in prod. |
| Existing defenses | None (no FORWARDED_ALLOW_IPS anywhere in repo). |
| Recommended fix | Set `FORWARDED_ALLOW_IPS` to Render's documented proxy CIDR (never `*`); then key anon limits on the *first untrusted* XFF hop; keep login limit per-IP but raise to a safe per-IP value; add a site-wide login circuit breaker as backstop. |
| Verification | Deploy with explicit `FORWARDED_ALLOW_IPS`; check `/health`-adjacent debug log of `client.host` from two different networks; unit test identifier picks XFF when proxy trusted, ignores it otherwise. |

## SEC-DOS-004 — No request-body size limit: large JSON bodies OOM the worker
| Field | Value |
|---|---|
| Severity / Confidence | **High / High** |
| Component | `main.py` (no body-size middleware anywhere), `api/chat.py:151` (`ChatMessageCreateRequest.question` ≤4000 chars but raw body unbounded), `api/change_set.py:59-75` + `domain/change_set.py:263` (`operations: list[ChangeSetOperation]` has `min_length=1`, **no max**) |
| Entry point | Any POST/PUT/PATCH (chat messages, change-set propose, progress, candidates ingest) |
| Data flow | Client body → Starlette reads entire body into memory → pydantic parses/validates → route |
| Vulnerability | No `Content-Length`/size cap; a 500MB JSON body is fully buffered then validated (pydantic may also expand it). Free-tier Render RAM (~512MB) ⇒ 1-2 concurrent huge bodies OOM-kill the app. `operations` list unbounded ⇒ a single propose body can carry 100k operations ⇒ huge validation loop + one giant Neo4j write. |
| Attack scenario | 3 parallel POSTs with 200MB bodies to any JSON route ⇒ worker OOM/restart loop. Or one 100k-op change-set proposal ⇒ seconds-long CPU + giant DB transaction. |
| Impact | Availability (app restart loop), Neo4j write amplification, log flooding. No direct $ (LLM) impact. |
| Reproduction (safe math) | 512MB container − uvicorn baseline ≈ <300MB free; two 200MB buffered bodies exceed it. No flood required to demonstrate arithmetic. |
| Existing defenses | None. |
| Recommended fix | Middleware rejecting `Content-Length > N` (e.g. 64KB-1MB per route class) + streaming body size guard; cap `operations` at e.g. 50; set `limits` on uvicorn (`--limit-max-requests` irrelevant; use app-level). |
| Verification | `curl -H 'Content-Length: 104857601' -d @/dev/zero ...` ⇒ 413 before route; unit test with 100k-op payload ⇒ 422. |

## SEC-DOS-005 — Visualization cache-key explosion via attacker-controlled focus sets (Redis memory + Neo4j recompute)
| Field | Value |
|---|---|
| Severity / Confidence | **High / High** |
| Component | `api/graph.py:188-192,239-241,280-288` (`focus_id` query param, ≤20 ids), `cache/graph_cache.py:155-167,200-201` (`focus_sig` = SHA-256 of set in key), `services/visualization.py:692-710` (dedupe, cap 20), `domain/visualization.py:63,68` |
| Entry point | `GET /api/series/{id}/graph/visualization?view=graphrag_focus&focus_id=...` — **anonymous allowed** (OptionalUserDependency) |
| Data flow | focus_id set → `focus_signature()` → unique `viz:{series}:{boundary}:{view}:{ver}:{user/anon}:{epoch}:{sig}` key → miss ⇒ `fetch_graph` (7 parallel Neo4j queries) + projection ⇒ SETEX with full VisualizationDTO payload, TTL 300s |
| Vulnerability | Key contains an attacker-controlled 2^256-space signature. Visible node ids are public (GET /graph). With ~1,000 visible nodes: 1,000 single-id sets, ~500k double-id sets — attacker enumerates combinations; each unique set = a new ~100KB-1MB Redis entry for 300s. No rate limit on graph GETs at all. |
| Attack scenario | Scripted loop over focus combinations at 50-100 req/s (single laptop, no auth): 300s TTL × 100/s = 30k live keys ≈ 3-30GB Redis (Upstash free tier = 30MB, paid per GB) ⇒ **Redis eviction/memory bill**; every miss also runs the full 7-query graph fetch ⇒ Neo4j CPU saturation. |
| Impact | Denial-of-wallet (Upstash memory $), Neo4j DoS for legit users. $: Upstash ~$0.15-0.20/GB-month storage+; 30GB spike ⇒ $5-6/mo base but eviction storm degrades all cache users; the Neo4j amplification is the bigger cost (each request = 7 queries × ~100ms ⇒ 7 query-seconds per 10 requests; 360k req/hr ⇒ ~700 query-hr/hr of Neo4j time). |
| Reproduction (safe math) | C(1000,1)=1,000 and C(1000,2)≈500k distinct signatures — combinatorics only, no live calls. |
| Existing defenses | 20-id cap, focus-id visibility validation (422 on hidden/unknown), TTL 300s. None address key cardinality. |
| Recommended fix | Don't put focus signature in the key: cache the *base* projection per (series, boundary, view, user) and apply focus selection post-cache (projection is deterministic over the safe graph); or cache only the top-K focus sets; add rate limit + per-IP/session cache-write budget; reduce TTL. |
| Verification | Unit test: 2 focus sets differing by one id ⇒ assert they share the base cache entry after fix; assert focus application is idempotent over cached payload. |

## SEC-DOS-006 — Unbounded chat history: session detail and every LLM turn read ALL messages
| Field | Value |
|---|---|
| Severity / Confidence | **Medium / High** |
| Component | `graph/chat.py:58-68` (`CHAT_MESSAGE_LIST_QUERY` — **no LIMIT**), `repository/chat.py:176-216`, `services/chat.py:306-308, 273-275`, `api/chat.py:97-104` |
| Entry point | `GET /api/series/{id}/chat/sessions/{sid}`; every chat turn (history load) |
| Data flow | session grows at 20 msgs/min (chat-send limit) ⇒ 28,800 msgs/day ⇒ every GET returns all rows; every turn's context pre-pass reads all rows into memory |
| Vulnerability | No pagination, no LIMIT, no message-count cap. Response size grows linearly with session age; per-turn DB read grows too (context render is capped at 40 items, but the DB fetch and row materialization are not). |
| Attack scenario | One account runs 20 msg/min for a day in one session (cheap non-LLM turns: send, immediately disconnect stream → still persists user message + runs pipeline? — yes, message is persisted before generation, so failed turns still grow history). Then GET the session ⇒ multi-MB response; repeat turns ⇒ growing per-turn latency. |
| Impact | Memory/CPU/response amplification; Neo4j query time growth. Modest $, real degradation. |
| Reproduction (safe math) | 28,800 rows × ~1-2KB avg (content+citations JSON) ≈ 30-60MB per session detail response. |
| Existing defenses | None (context render cap only affects prompt, not the query). |
| Recommended fix | LIMIT + cursor pagination on `CHAT_MESSAGE_LIST_QUERY`; cap history passed to LLM at N most-recent messages (windowed); cap sessions per user. |
| Verification | Unit test: seed 5,000 messages ⇒ GET returns page of 50; assert LLM turn query has LIMIT. |

## SEC-DOS-007 — Cheap cache-flush DoS: user writes invalidate the entire series cache; unbounded custom-node growth bloats the shared graph
| Field | Value |
|---|---|
| Severity / Confidence | **Medium / High** |
| Component | `api/user_content.py:122,144,160,173,195,211` (`invalidate_series` per write), `cache/graph_cache.py:115-137` (epoch INCR + scan_iter DEL of all `graph:*`/`viz:*` keys), `api/change_set.py:116,188` |
| Entry point | POST/PATCH/DELETE custom-nodes / custom-relationships (authenticated, 30/min/user), confirm/revert change-set |
| Data flow | 1 write → epoch bump + delete of every cached graph/viz payload for the series → next reader pays full 7-query fetch_graph |
| Vulnerability | Write:read cost ratio ≈ 1:7+ queries per subsequent reader. With account farming (N × 30/min) an attacker invalidates a series' whole cache continuously ⇒ all legit readers always miss ⇒ Neo4j load multiplied; each write also adds a custom node/relationship to the shared graph, and `fetch_graph` has **no LIMIT** on nodes/claims/evidence/sources (`spoiler/filter.py` queries) ⇒ graph growth makes every read slower for everyone forever. |
| Attack scenario | 3 accounts × 30 writes/min = 90 invalidations/min on the flagship series ⇒ permanent cache miss rate for all users; add 1,500 custom nodes/day ⇒ fetch_graph payload and query time grow monotonically. |
| Impact | Neo4j CPU/query-time DoS, growing response payloads (also inflates SEC-DOS-005 Redis payload sizes). No direct LLM cost. |
| Reproduction (safe math) | 1 write ⇒ ≥7 cached queries destroyed per subsequent reader; 90/min ⇒ ~10k+ extra queries/hr if the series gets ~2 req/s. |
| Existing defenses | content-write 30/min/user (farmable); TTL bounds cache size. |
| Recommended fix | Coalesce/debounce invalidation (dirty-flag per series, sweep at most once per few seconds); scope cache keys so user-content writes don't nuke canonical graph entries (they already filter user_authored out — consider caching user nodes separately); cap custom-node creation per user/series; add LIMITs to fetch_graph projections. |
| Verification | Unit test: 100 writes in 10s ⇒ assert ≤2 cache invalidations; assert custom-node writes don't delete canonical-graph cache entries. |

## SEC-DOS-008 — Concurrency gaps: per-user slot is in-process only; unbounded parallel turns multiply LLM/Neo4j load
| Field | Value |
|---|---|
| Severity / Confidence | **Medium / High** |
| Component | `services/chat.py:45-74` (`_concurrent_generations` dict, `_MAX_CONCURRENT_GENERATIONS_PER_USER = 1`), `render.yaml:10` (1 worker today), `retrieval/pipeline.py:780-878` (5 sequential provider calls, 60s timeout each) |
| Entry point | `POST .../messages` and `/messages/stream` |
| Data flow | N accounts → N parallel turns → each up to 5 concurrent outbound provider calls + Neo4j queries, each turn up to 300s wall time |
| Vulnerability | (a) The dict is per-process: any move to >1 worker multiplies per-user concurrency by worker count. (b) Even at 1 worker, N accounts = N concurrent full pipelines (asyncio interleaves; the worker is not blocked but the *provider and Neo4j* see N×5 concurrent calls). (c) SSE clients that connect and stall hold a slot + provider connection for up to 300s per turn — cheap for the attacker (one socket), expensive server-side. (d) Slot dict entries are never removed at 0 (`_release_generation_slot` leaves `user_id: 0`) ⇒ unbounded dict growth across distinct users. |
| Attack scenario | 50 accounts × 1 stalled SSE stream each ⇒ 50 concurrent turn pipelines, up to 250 provider connections + 350+ Neo4j queries in flight; Upstash/Neo4j connection pools saturate; legit users queue. |
| Impact | Availability + wallet: provider concurrency also burns tokens on turns nobody consumes. |
| Reproduction (safe math) | 50 concurrent turns × (4 tool rounds + 1 final) = 250 provider calls in flight; Neo4j pool max 50 (`graph/database.py:70`). |
| Existing defenses | Per-user slot (farmable), per-user 20/min (farmable). No global semaphore, no connection caps. |
| Recommended fix | Process-wide asyncio semaphore on LLM calls (e.g. 4-8); per-IP concurrency cap; release/cancel provider call when SSE client disconnects (already aborts via GeneratorExit — keep); prune slot dict; require BYOK for unauthenticated-style load. |
| Verification | Unit test: 2 users concurrently ⇒ second is 429 only if global semaphore added; assert dict size bounded after N users. |

## SEC-DOS-009 — Unthrottled write endpoints: session create/delete, progress update, change-set propose, share-link create
| Field | Value |
|---|---|
| Severity / Confidence | **Medium / High** |
| Component | `api/chat.py:62-69,107-133` (no limiter), `api/progress.py:83-110` (no limiter), `api/change_set.py:59-75,120-189` (propose/reject/revert unlimited), `api/share.py:39-92` (create unlimited) |
| Entry point | POST/PATCH/DELETE above (all authenticated + CSRF origin) |
| Data flow | Each request = 1+ Neo4j writes (session node, message node, progress upsert, change-set draft + N operations, share token) |
| Vulnerability | Only message-send and content-write have limiters. An attacker can create unlimited chat sessions, share tokens, change-set drafts, and progress records — pure DB write amplification and unbounded storage growth (session list/`list_share_links` queries also degrade). Progress writes churn the per-user graph cache key space (boundary in key ⇒ alternating boundaries = new keys). |
| Attack scenario | Script creates 10k sessions + 10k share tokens + 10k change-set drafts in an hour (1 process, ~3 req/s) ⇒ Neo4j node bloat; session sweeps (hourly) only clean sessions, not drafts/tokens beyond TTL. |
| Impact | Storage growth (Aura paid per GB), query degradation, share-token table bloat (each token = a brute-forceable graph entry point, see S-other). |
| Reproduction (safe math) | 10k sessions × ~300B + 10k tokens ≈ few MB/day per attacker; linear, unbounded. |
| Existing defenses | CSRF origin guard (defeated by scripts sending Origin header), hourly expired-session sweep. |
| Recommended fix | Extend `content_write_rate_limiter` (or a new per-user write limiter) to session create, change-set propose/reject/revert, share create, progress upsert; cap sessions per user; TTL drafts. |
| Verification | Unit test asserting 429 on 31st session-create in a minute after fix. |

## SEC-DOS-010 — Unauthenticated heavy read endpoints: graph expand + path are uncached, unthrottled, anonymous
| Field | Value |
|---|---|
| Severity / Confidence | **Medium / High** |
| Component | `api/graph.py:304-386` (`/graph/expand` — deliberately no cache, anonymous), `:466-499` (`/graph/path` POST, anonymous, `max_hops` ≤4), `services/graph.py:51-128` (`fetch_graph` = 7 parallel queries, no LIMIT), `retrieval/tools.py:350-421,565-635` (BFS with unbounded `CLAIMS_FOR_FRONTIER_QUERY` rows) |
| Entry point | GET `/graph/expand`, POST `/graph/path` without session |
| Data flow | Anonymous → boundary resolve (2 queries) → full `fetch_graph` (7 queries) → projection/BFS |
| Vulnerability | These are the most expensive anonymous endpoints and have **no rate limit and no cache** (expand by design, path never cached). Each request runs the full 7-query graph read; path additionally runs up to 4 BFS hops where each hop's claim query has no LIMIT (row count bounded only by graph density). |
| Attack scenario | Single laptop, 20-50 req/s of expand/path on the flagship series ⇒ 140-350 Neo4j queries/s; Aura free tier (2 vCPU, shared) saturates ⇒ all users' graph reads slow to a crawl. |
| Impact | Availability (Neo4j CPU), no direct $. |
| Reproduction (safe math) | 30 req/s × 9 queries ≈ 270 q/s sustained; Aura free tier advertises ~50-200 q/s practical. |
| Existing defenses | max_hops ≤4, expansion limit ≤25, boundary fail-closed. No rate limit, no cache. |
| Recommended fix | Anonymous read rate limit (per-IP, honoring proxy chain per SEC-DOS-003) on graph/expand/path; cache expand deltas per (series, boundary, key, anchor) — the D-21 tuple is deterministic; keep path behind optional auth. |
| Verification | Unit test/observed: 429 after N anonymous expand requests once limiter wired; benchmark one expand = 9 queries. |

## SEC-DOS-011 — Redis key growth without bound: per-user rate-limit ZSET keys and per-user graph cache keys never expire as keys
| Field | Value |
|---|---|
| Severity / Confidence | **Low / Medium** |
| Component | `services/rate_limit.py:84,91` (key `user:{id}:hdgraf:rate_limit:20/60` — pyrate-limiter prunes ZSET *entries* via in-process Leaker but the ZSET key persists per distinct user), `cache/graph_cache.py:71-72,155-167` (per-user graph/viz keys, TTL 300s bounded but key count ∝ users×series×boundaries×focus_sig) |
| Entry point | Any chat/content-write request (creates limiter ZSET), any graph GET (creates cache key) |
| Data flow | Distinct user ids (account farming) → distinct Redis keys forever |
| Vulnerability | Upstash bills keyspace + per-key overhead; a farm of 10k users ⇒ 10k+ permanent limiter ZSETs (no TTL on the key itself). Cache keys are TTL-bound but the *cardinality* is unbounded per SEC-DOS-005. |
| Attack scenario | Automated account farm over weeks ⇒ tens of thousands of permanent Redis keys. |
| Impact | Small but permanent Redis memory/wallet growth; compounds SEC-DOS-005. |
| Reproduction (safe math) | 10k users × ~200B key+ZSET ≈ 2MB — small; the issue is permanence at scale. |
| Existing defenses | Leaker daemon prunes entries; TTL on cache payloads. |
| Recommended fix | EXPIRE the ZSET key itself (e.g. 2× window) after the last entry ages out; periodic keyspace sweep for orphaned `user:*` limiter keys. |
| Verification | Inspect Redis `SCAN user:*` after a test user's window elapses — key should be gone after fix. |

## SEC-DOS-012 — Per-request httpx clients and INFO log flooding amplify small attacks
| Field | Value |
|---|---|
| Severity / Confidence | **Low / High** |
| Component | `llm/provider.py:130-133,336` (new `httpx.AsyncClient` per provider instance = per chat request; no pooling across requests), `main.py:76-101` (INFO log line per request incl. user-agent) |
| Entry point | Any chat request (client churn), any endpoint (log volume) |
| Data flow | Request → provider construction → new connection pool → 5 sequential calls → pool GC'd |
| Vulnerability | No connection reuse: each chat turn pays TCP+TLS setup per request (5 calls reuse the per-request client, but the client itself is per-request). Under farm load (SEC-DOS-002), connection churn adds CPU/socket pressure. Log middleware writes one INFO line per request — a 100 req/s scripted flood = 8.6M log lines/day ⇒ disk/log-ingestion cost and I/O. |
| Attack scenario | Combined with SEC-DOS-002/010: log + socket amplification of every request. |
| Impact | Minor CPU/IO; log ingestion cost on managed logging. |
| Reproduction (safe math) | 100 req/s × 86,400 s = 8.64M lines/day ≈ 1-2GB logs. |
| Existing defenses | None (headers are allowlisted — no secret leakage, but volume unbounded). |
| Recommended fix | Share one `httpx.AsyncClient` per provider config (module-level, keyed by base_url); rate-limit INFO logging (sample or move to DEBUG per-request, keep WARN+). |
| Verification | Assert single client instance across N requests in unit test; count log lines at 100 req/s. |

---

## Worst-case amplification summary (one anonymous request)

| Endpoint (anonymous) | LLM calls | Neo4j queries | Redis ops | Cache write |
|---|---|---|---|---|
| `GET /graph` | 0 | 7 (cached under shared `anon` key) | 1 GET + 1 SETEX | yes |
| `GET /graph/visualization?view=graphrag_focus&focus_id=…` | 0 | 7 + projection | 2 GET + 1 SETEX | **yes — unique key per focus set** |
| `GET /graph/expand` | 0 | 7 + projection | 0 | no (by design) |
| `POST /graph/path` | 0 | 2 + ≤4 BFS hops | 0 | no |
| `POST /api/auth/google` | 0 | 1-2 | 1 ZADD (if Redis) | — |

| Endpoint (authenticated, 1 account) | LLM calls | Max input tokens | Max output tokens | $ (Gemini 2.5 Flash ref) |
|---|---|---|---|---|
| 1 chat turn (worst case, 4 tool rounds + final) | 5 | ~40-60k | ~4k | ~$0.02-0.03 |
| 1 account at 20 msg/min for 24h | 144,000 calls | ~60M | ~5.8M | ~$25-36/hr ⇒ **~$600-860/day** |
| 10-account farm | 1.44M calls/day | ~600M | ~58M | **~$6-8.6k/day** |

**Top priorities:** SEC-DOS-002 (wallet), SEC-DOS-001 (limit fail-open), SEC-DOS-005 (cache-key explosion), SEC-DOS-003 (login DoS), SEC-DOS-004 (OOM).
