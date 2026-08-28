# AuraDB Free provisioning + Neo4j driver 6.x TLS (verified live 2026-08-04, phase 08 deploy)

## AuraDB Free credentials reality — "Member" console role is NOT a DB credential

- Console roles (Project Settings → Users: `ORG_MEMBER`, `PROJECT_MEMBER`, etc.) are **human console access**, not database credentials. Aura docs: "User management within the Aura console does not replace built-in roles or fine-grained RBAC at the database level."
- `CREATE USER ... SET PASSWORD ... CHANGE NOT REQUIRED` via the Query browser is **DENIED on AuraDB Free**:
  - Console tool-auth connects as a UUID user with the immutable DBMS role `console_admin_free_<dbid>` → `Neo.ClientError.Security.Forbidden: Permission has not been granted for CREATE USER`.
  - Even the credentials-file instance admin gets `42NFF: Syntax error or access rule violation - permission/access denied`.
  - The docs' Connect-instance "Option 1" (CREATE USER) applies to paid tiers only.
- **Working setup:** single credential — the instance admin from the downloaded credentials file: `NEO4J_URI=neo4j+s://<dbid>.databases.neo4j.io`, `NEO4J_USERNAME=<dbid>`, `NEO4J_DATABASE=<dbid>`. D-16 least-privilege is a documented Free-tier ceiling; if a paid tier is ever used, create a Member app user then.
- First diagnostic for any forbidden admin command: `SHOW CURRENT USER;` — shows the connected identity + DBMS roles (UUID + `console_admin_free_*` = console tool-auth, not the instance credential).

## neo4j python driver 6.x TLS — SSLCertVerificationError on Windows

**Symptom:** `neo4j.exceptions.ServiceUnavailable: Unable to retrieve routing information` (an ExceptionGroup swallowing the real cause).

**Diagnostic ladder:**
1. TCP probe first (DNS + ports 7687/443/7474) — rules out network.
2. Unwrap the cause chain (`e.__cause__`, then `.exceptions` on ExceptionGroups) → real error: `[SSLCertVerificationError] certificate verify failed: self-signed certificate in certificate chain`.
3. Raw TLS test to isolate driver vs trust store:
   ```python
   ctx = ssl.create_default_context(cafile=certifi.where())   # certifi bundle
   ctx2 = ssl.create_default_context()                        # OS/OpenSSL defaults
   ```
   certifi OK + OS store FAIL ⇒ **Windows cert store is missing/stale a root**. Aura's chain: `CN=neo4j.io` → SSL.com RSA SSL subCA → SSL.com Root RSA → Certum Trusted Network CA cross-sign.

**Fix (driver 6.x — committed in `database.py`):** the `neo4j+s://` scheme REJECTS explicit `encrypted=`/`trusted_certificates=` kwargs (`ConfigurationError: ... can only be used with the URI schemes ['bolt', 'neo4j']`). Normalize the scheme and pass them explicitly:

```python
uri = uri.replace("neo4j+s://", "neo4j://").replace("bolt+s://", "bolt://")
kwargs["encrypted"] = True
kwargs["trusted_certificates"] = TrustCustomCAs(certifi.where())
```

Equivalent TLS + full chain verification, deterministic on Windows and Linux/Render. Declare `certifi` as a direct dependency (`uv add certifi`) — importing a transitive dep directly is fragile.

**Reseed Aura from the local machine:** use the venv python, NOT `uv run` — repo root `.python-version` pins 3.13 while the venv is 3.11, so `uv run` tries to fetch a new interpreter. Pattern that worked:
```bash
unset PYTHONPATH && source .venv/Scripts/activate
NEO4J_URI='neo4j+s://<dbid>.databases.neo4j.io' NEO4J_USERNAME='<dbid>' \
NEO4J_PASSWORD='...' NEO4J_DATABASE='<dbid>' python -m backend.app.graph.setup
```
(Background + notify_on_complete; success prints e.g. "Dexter graph setup complete: 41 nodes, 26 relationships").

## Vitest verification on this repo

- **Full-suite 5s timeouts on heavy jsdom tests (App.test.tsx, SettingsPage.test.tsx) ROTATE across runs under parallel load — flaky, not a regression.** Failing set changes every run; isolated file runs pass. Confirm with `npx vitest run --no-file-parallelism` (serial) before chasing ghosts.
- **VITE_API_BASE_URL double-prefix trap:** when a fetch client starts prefixing `VITE_API_BASE_URL`, audit ALL `frontend/.env*` files — a stale `VITE_API_BASE_URL=/api` in `.env.local` (from the old example) silently double-prefixes (`/api/api/...`) in local dev AND vitest (vite loads `.env.local` in test mode). Local dev must leave the var unset (Vite proxy handles `/api`); production origin set as a Vercel project env var.

## 08-01 deploy checklist (human actions — no CLI path on free tiers)

1. Render: New → **Blueprint** from committed `render.yaml` (uv sync --frozen / uvicorn); env: `NEO4J_URI/USERNAME/PASSWORD/DATABASE` (Aura), `GOOGLE_CLIENT_ID`, `SESSION_COOKIE_SECURE=true`, `FRONTEND_ORIGINS=https://app.spoilerless.net`, `ALLOWED_EMAILS`; custom domain `api.spoilerless.net`.
2. Vercel: Root Directory `frontend/`, env `VITE_API_BASE_URL=https://api.spoilerless.net` + `VITE_GOOGLE_CLIENT_ID` (Production and Preview); custom domain `app.spoilerless.net`.
3. Cloudflare: CNAME `app` → Vercel target hostname, `api` → Render target hostname.
4. Google Cloud Console: add `https://app.spoilerless.net` to OAuth client authorized JavaScript origins AND redirect URIs (else `redirect_uri_mismatch`).
