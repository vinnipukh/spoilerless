# Backend Deploy Crash — Root Cause & Fix

**Date:** 2026-08-05  
**Error:** `ModuleNotFoundError: No module named 'backend'`

---

## Root Cause

Render's **dashboard start command** has been manually set to:
```
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

But the Python package is named `spoilerless/`, not `backend/`. There is no `backend/` directory in the repo.

The `render.yaml` in the repo has the **correct** command:
```yaml
startCommand: uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT
```

However, **Render dashboard overrides take precedence over `render.yaml`** for existing services. Someone (likely the sibling agent Hermes) changed the start command in the Render dashboard to reference `backend.app.main:app`.

## Fix (Manual — Render Dashboard)

1. Go to https://dashboard.render.com → **spoilerless-api** service
2. **Settings** → **Start Command**
3. Change from: `uv run uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
4. Change to: `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`
5. Click **Save Changes** → service will auto-redeploy

Alternatively, delete and re-create the service from the Blueprint (`render.yaml`) which already has the correct value.

## Verification

- `pyproject.toml` → `name = "spoilerless"`, script entry: `spoilerless.app.graph.setup:main`
- `render.yaml` → `startCommand: uv run uvicorn spoilerless.app.main:app ...`
- Package directory: `spoilerless/app/main.py` exists ✅
- `backend/` directory: **does not exist** ❌

---

## Backend Tests — Break Up Strategy

The full `uv run pytest` suite takes too long to run synchronously, which means broken backend code ships without being caught. Break into targeted runs:

```powershell
# Group 1: Core domain & models (~fast)
uv run pytest spoilerless/tests/test_models.py spoilerless/tests/test_domain*.py -q

# Group 2: API routes (~medium)
uv run pytest spoilerless/tests/test_api*.py -q

# Group 3: Graph/Neo4j services (~slow, needs fixtures)
uv run pytest spoilerless/tests/test_graph*.py -q

# Group 4: Auth & middleware
uv run pytest spoilerless/tests/test_auth*.py spoilerless/tests/test_middleware*.py -q

# Group 5: Contract & doc tests
uv run pytest spoilerless/tests/test_frontend_contract*.py spoilerless/tests/test_export*.py -q
```

Run these as parallel async tasks. If any group fails, you catch it in seconds instead of waiting for the full suite.
