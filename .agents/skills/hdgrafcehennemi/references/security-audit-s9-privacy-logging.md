# Security audit 2026-08-14 — S9: Privacy, Logging & Information Disclosure

Part of `.planning/quick/20260814-security-audit/` (subagents S1–S9). Full findings: repo path
`.planning/quick/20260814-security-audit/findings/S9-privacy-logging.md` (9 findings, SEC-LOG-001..009).
This reference keeps the reusable checks and the one genuinely novel pitfall close to future audit runs.

## Reusable FastAPI pitfall (verified empirically, not just theory)

**`logger.error("...", exc_info=exc)` on a `RequestValidationError` writes RAW submitted input values
to server logs.** `str(RequestValidationError)` = `json.dumps(errors())`, and errors() entries carry an
`input` key (FastAPI >= 0.100) with the full rejected value.

Verified with the repo's FastAPI:

```python
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
class M(BaseModel):
    question: str = Field(min_length=1, max_length=10)
try:
    M.model_validate({'question': 'x' * 20})
except Exception as e:
    err = RequestValidationError(e.errors())
    assert 'input' in err.errors()[0] and 'x' * 20 in str(err)
```

Consequences found in this repo (`core/errors.py` validation_handler):
- Chat `question` > 4000 chars rejected → full message text in logs (chat/PII at rest, no retention).
- Malformed Google `credential` body → submitted JWT/ID-token material in logs.

Fix pattern: log only `[{k: e[k] for k in ("loc","msg","type")} for e in exc.errors()]`, drop
`input`/`ctx`; or redact sensitive fields (`credential`, `password`, `token`, `question`).

## Audit checklist used (reuse for the next security audit pass)

Backend (grep `logger.|print(|loguru|structlog` across `spoilerless/`; skip tests):
1. Request-log middleware: does it log headers dict / cookie / authorization / body? (Here: allowlist of
   method, path, status, ms, user-agent/content-type/accept only — `main.py:_request_logging_middleware`.)
2. `/health` fields: status/database/service only — no db name, version, env, redis. `service` literal
   `"spoilerless-backend"` is still a mild fingerprint (SEC-LOG-005).
3. Error envelope: canonical ERROR_CODES registry, `extra="forbid"`, generic messages; stream errors
   generic to client, real exception logged server-side; no custom 500 handler + no `debug=True` = safe
   Starlette default. Watch validation_handler (see pitfall above).
4. Session/token hygiene: raw token never stored (SHA-256 hash only), cookie HttpOnly+Secure+SameSite,
   hourly sweep of expired/revoked sessions.
5. LLM key: must appear only in provider constructor; grep that X-LLM-* headers are excluded from logs.
6. Headers: CSP/HSTS/nosniff/XFO/Referrer-Policy present; CORS explicit origins + credentials with
   explicit methods/headers (never wildcard+credentials); **TrustedHostMiddleware absent** (SEC-LOG-006);
   **/docs + /openapi.json exposed by default** (SEC-LOG-004).
7. Chat data: stored in Neo4j indefinitely (no TTL on messages), full history sent to LLM provider each
   turn (SEC-LOG-007); user_id in Redis cache/rate-limit keys (SEC-LOG-008); uvicorn default access log
   logs client IPs (SEC-LOG-009).

Frontend (grep `console\.(log|debug|info)`, `localStorage`, `sessionStorage`, `sentry|telemetry|analytics`):
- Here: zero console.log in src/, zero telemetry, chat content never in browser storage (in-memory only),
  watch progress in sessionStorage only. BYOK LLM API key in plaintext localStorage = documented
  tradeoff (SEC-LOG-003), mitigated by backend log exclusion of X-LLM-*.

## Verified strong controls (do NOT re-flag on the next pass)

Request-log allowlist; hashed session tokens + sweep; sanitized error envelope (no client tracebacks);
LLM key never logged/persisted; no frontend telemetry/console logging; CSP + HSTS + nosniff + XFO DENY +
Referrer-Policy; CORS + CSRF origin guard on state-changing routes; chat/LLM never cached in Redis.

## Findings-file format contract (used across S1–S9)

Per finding: ID (SEC-LOG-nnn) | Title | Severity | Confidence | Component (file:line) | Entry point |
Data flow | Vulnerability | Attack scenario | Impact | Reproduction | Existing defenses | Recommended
fix | Verification. End with a "verified controls" section so later passes don't re-flag known-good code.
