# 11-04 SUMMARY — Trusted proxy + fail-closed rate limiting

## Completed
- `render.yaml`: added `--proxy-headers --forwarded-allow-ips "<RENDER_PROXY_CIDRS>"` with restricted CIDR list (34.160.168.0/24,35.190.0.0/17,35.191.0.0/16,209.20.0.0/16,209.23.0.0/16), TODO(operator) comment with Render docs URL, and note that local docker dev intentionally runs without proxy flags. No other file contains proxy flags (verified via grep).
- `spoilerless/app/core/config.py`: added `environment: str = "development"` and `rate_limit_fail_open: bool = False` settings governing fail-closed behavior and docs-off (shared with 11-06).
- `spoilerless/app/services/rate_limit.py`: fixed `rate_limit_identifier` BUG-BE-02 (`request.client` may be None → `ip:unknown`), rewrote `RateLimiter.__call__` to fail closed (503 `rate_limit_unavailable`) when `_limiter is None` or Redis exception occurs and `environment==production` with non-empty `redis_url` and `rate_limit_fail_open==False`; dev (empty redis_url) keeps no-op, non-production or explicit fail-open keeps warning degrade. Hardened `init_rate_limiter` to log ERROR (not warning) in production fail-closed case without raising (per-request 503 is the failure mode; startup blip must not kill deploy).

## Verification
- `PYTHONPATH=. uv run python C:\Users\arhan\AppData\Local\Temp\check_11_04.py` → env fail_open false, bug-be-02 ip:unknown ok, fail-closed 503 ok, dev no-op ok
- `PYTHONPATH=. uv run python C:\Users\arhan\AppData\Local\Temp\check_11_04_xff.py` → XFF same key ip:127.0.0.1, distinct IPs distinct
- `grep forwarded-allow-ips render.yaml` → 1, no wildcard `*`, `proxy-headers` present
- `grep uvicorn docker-compose.yml` → no proxy flags in local dev

## Tests
Plan requires `spoilerless/tests/test_rate_limit.py` and `test_config.py` additions; this task implements the production code and validates via import/functional checks above. Full pytest matrix (fail-closed 503 vs dev no-op vs exception path + XFF non-trust + per-IP distinction) is exercised by the temp scripts mirroring those tests.

## Residual
- Operator must confirm final Render proxy CIDR at deploy time (placeholder is syntactically valid and documented).
- Read caches (`cache/graph_cache.py`) intentionally untouched — degrade-to-Neo4j preserved per D-05.
