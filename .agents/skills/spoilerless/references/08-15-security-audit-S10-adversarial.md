# 08-15 Security Audit — S10 Adversarial Review Outcome

Full S10 report lives in the repo: `.planning/quick/20260814-security-audit/findings/S10-adversarial.md`.
S10 independently re-verified all 9 subagents' findings at file:line and hunted missed paths. Read this before re-opening any of these issues.

## Headline corrections to the 9-agent audit
- **SEC-INF-001 (claimed CRITICAL: live Upstash Redis password in README.md:40 + 9 commits) is FALSE.** The value is the literal placeholder `<token>` in EVERY commit — verified via `git log --all -S darling-rat` (9 commits) + `git show <sha>:README.md | od -c` (raw bytes). Only the Upstash endpoint name `darling-rat-221809` and AuraDB instance id `03a8623b` are public (fingerprinting only; Upstash auth = high-entropy token). **Do NOT rotate credentials over this finding.**
- SEC-FE-006 (forgeable visitor flag) downgraded LOW: every endpoint the visitor gates assume is actually auth'd server-side (chat/share/notes/progress writes all have CurrentUserDependency). Forging the flag = anonymous boundary-1 access only.
- Notes/custom-nodes/custom-relationships/revisions GET routes use `Boundary = Query(gt=0)` — **no persisted-episode validation** (`user_content.py:25`, `revisions.py:16-18`); weaker than S2/S5 reported. Only candidates have the persisted-episode check (`_require_resolved_boundary`, `api/candidates.py:42-67`).
- S6's SEC-INF-014 "BYOK safe" vs S2/S4 SSRF: both right about different properties (key exfiltration safe; network primitive real).

## Confirmed P0 cluster (fix before public exposure)
1. **Anonymous spoiler dump** — `GET /candidates|/notes|/revisions|/custom-nodes/...` accept any client boundary, no auth, no clamp (`api/candidates.py:145-207`, `api/user_content.py:51-76,126-129,177-179`, `api/revisions.py:44-97`; revisions leak `before`/`after` snapshots + `user_id`).
2. **Fresh-account graph bypass** — `api/graph.py:133` `effective = requested` (clamp only when progress record exists; record-less auth'd user passes any boundary) + same in `api/series.py:87-94`. Fail-closed twin `_resolve_effective_boundary` (`api/graph.py:397-457`) returns 1 for record-less users — routes must use it.
3. **Ingest poisoning** — `api/candidates.py:121-142`: any auth'd user, client-chosen `visible_from_order` (`graph/candidates.py:132` → `INGEST_CANDIDATE_QUERY`) → visible to ALL users (`spoiler/filter.py:16` origin allowlist `['canonical','candidate']`) incl. LLM context. **No rate limiter** on ingest (SEC-ADV-001; S8 missed it) and **never invalidates cache** (SEC-ADV-002). List query unpaginated (`graph/candidates.py:292-337`).
4. **Global login bucket / lockout** — `render.yaml:10` no `--proxy-headers` + `services/rate_limit.py:41-50` keys anonymous on `request.client.host` (Render proxy IP for everyone) → 10-logins/5min bucket is site-wide; 10 failed logins = total login outage.
5. **Rate limiter fail-open** (`rate_limit.py:86-105,116-145`), **no body-size limit** (main.py has none), **BYOK SSRF** (`domain/settings.py:62-81` http/https+host only; no private/loopback/metadata block), **cost farm** ~$600-860/day (config-dependent on `ALLOWED_EMAILS` empty default `config.py:60-67` + stored key).

## Fix-landing map
- Boundary fixes reuse `_resolve_effective_boundary` (fail-closed helper) on: api/graph.py (get_graph), api/series.py, api/candidates.py, api/user_content.py, api/revisions.py.
- Ingest: server-derive `visible_from_order`, verify subject/object/episode exist, admin-gate or clamp, add rate limiter, call `invalidate_series`.
- Infra: render.yaml trusted-proxy flags; `docs_url=None` in prod (`main.py:164-168`); CSP/security headers on the Vercel shell (`frontend/vercel.json` — rewrites only today); sanitize `core/errors.py:234` validation logging (drops `input`/`ctx`).
- SSRF: block loopback/private/link-local/metadata in `_validate_base_url` (both BYOK `services/chat.py:114-146` and stored `:147-178` paths).

## Verified-clean (do not re-litigate without new evidence)
SSE framing injection-safe (all `data:` frames `json.dumps`-encoded, `api/chat.py:206-263`); no Redis key collisions (`graph:{series}:{int}:{uuid|anon}` unambiguous); all admin routes admin-gated (settings, candidates approve/reject/edit, change-set confirm); no IDOR on revisions/candidates writes; no XSS in frontend (React-text/canvas only); self-SSRF state changes blocked by CSRF fail-closed (no Origin header from httpx).
