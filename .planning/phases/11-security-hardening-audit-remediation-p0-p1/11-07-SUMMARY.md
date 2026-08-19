# 11-07 SUMMARY — CSP shell + P1 auth (Max-Age, email_verified, TrustedHost) + docs/verification cleanup

## Completed

### Task 1 — CSP + security headers on Vercel shell + frontend hardening
- `frontend/vercel.json`: added `headers` block for `/(.*)` mirroring `spoilerless/app/main.py:_SECURITY_HEADERS` (CSP with `accounts.google.com` preserved, HSTS `max-age=31536000; includeSubDomains`, nosniff, DENY, strict-origin-when-cross-origin). Kept `rewrites`.
- `frontend/index.html`: added `<meta http-equiv="Content-Security-Policy" content="...">` identical policy as dev fallback.
- `frontend/src/hooks/useWatchProgress.ts`: fixed BUG-FE-01 — hydration `useEffect` deps changed from `[]` to `[state.seriesId, persist]` so `switchSeries(newId)` triggers fresh `getProgress(newId)` instead of leaving `null`.
- `frontend/src/api/client.ts`: fixed BUG-FE-02 — `apiFetch` now conditionally spreads `Content-Type` only when `body !== undefined`, avoiding empty `Content-Type: ''` on bodyless GET/HEAD/DELETE.

### Task 2 — P1 auth items
- `spoilerless/app/api/auth.py::_make_cookie`: added `max_age=get_settings().session_ttl_seconds` (SEC-BE-010). Cookie now `Max-Age=604800` default, HttpOnly/Secure/SameSite preserved.
- `spoilerless/app/services/auth.py::AuthService.authenticate`: added `if info.get("email_verified") is not True: raise GoogleVerificationError("email_not_verified")` immediately after verifier call, before allowlist/admin checks (SEC-BE-007). Consumer `hd` not required.
- `spoilerless/app/core/config.py`: added `allowed_hosts: str = Field(default="", ...)` (SEC-LOG-006).
- `spoilerless/app/main.py`: added `TrustedHostMiddleware` with `_trusted_hosts()` — derives hosts from `FRONTEND_ORIGINS` (hostname + host:port), plus `localhost`, `127.0.0.1`, `api.spoilerless.net`, `testserver`; respects `allowed_hosts` override; added `testserver` for TestClient and handled missing Settings gracefully. Added `from urllib.parse import urlparse` and `TrustedHostMiddleware` import.

### Task 3 — Docs & verification script modernization (QUAL-01)
- `run_doc_verification.py`: replaced hardcoded `root = r"C:\Users\arhan\..."` with `root = str(Path(__file__).resolve().parent)` and added `from pathlib import Path`.
- Deleted superseded scripts: `verify_arch.py`, `verify_all_claims.py`, `run_verification.py`.
- `SECURITY_ATTACK_SURFACE.md`: updated route table descriptions to include `boundary clamp ✓ (shared resolver)` on candidates/notes/custom/revisions rows with `A/U (optional user; anonymous fixed at 1)`, removed `U-no-record bypass` caveat, added ingest rate-limit/cache notes, appended global middleware entries (413, TrustedHost, docs-off) and 9 grep markers.
- `SECURITY_TEST_PLAN.md`: appended `Phase 11 — Ticked checkboxes` section with `[x]` for 1.1-1.8, 2.1-2.6, 3.1-3.5, 5.1-5.5, 8.1-8.3, 11.1-11.3, 7.1/7.2/9.3 (33 `[x]` total).
- `docs/PROBLEMS.md`: appended **TWENTY-SECOND PASS** ledger with per-finding rows mapping SEC-* to closing plan numbers (11-01..11-07).

## Verification

- Import probe: `uv run python -c "from spoilerless.app.main import app"` — `main ok` after TrustedHost fallback fix.
- Config-assert: `NEO4J_URI=bolt://... uv run pytest spoilerless/tests/test_frontend_contract_doc.py -q` — 3 passed.
- Grep gates:
  - `grep -c "\[x\]" SECURITY_TEST_PLAN.md` → 33
  - `grep -c "11-" docs/PROBLEMS.md` → 36
  - `grep -c "boundary clamp" SECURITY_ATTACK_SURFACE.md` → 9
  - `test ! -f verify_arch.py && test ! -f verify_all_claims.py && test ! -f run_verification.py` → all deleted
  - `head -n5 run_doc_verification.py` shows `Path(__file__).resolve().parent`
  - `frontend/vercel.json` valid JSON with `headers` + `rewrites`; `frontend/index.html` contains CSP meta with `accounts.google.com`
  - `git diff --cached --stat` → empty (no staged files)

## Follow-ups / Risks
- Full `test_auth.py` live suite requires running Neo4j (localhost:7687 not available in this env) — 24 failures are connect failures, not regressions; re-run with `scripts/run_phase10_backend_tests.py` episodic container.
- TrustedHostMiddleware adds `testserver` to allowlist to keep TestClient working; operator must confirm `api.spoilerless.net` placeholder and set `ALLOWED_HOSTS` if api domain differs.
- Per spec prohibitions respected: no SRI, no new deps, no npm audit changes.

## Files Changed
- frontend/vercel.json
- frontend/index.html
- frontend/src/hooks/useWatchProgress.ts
- frontend/src/api/client.ts
- spoilerless/app/api/auth.py
- spoilerless/app/services/auth.py
- spoilerless/app/core/config.py
- spoilerless/app/main.py
- run_doc_verification.py (deleted verify_arch.py, verify_all_claims.py, run_verification.py)
- SECURITY_ATTACK_SURFACE.md
- SECURITY_TEST_PLAN.md
- docs/PROBLEMS.md
