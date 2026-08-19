# README re-verification after surgical fixes (2026-08-10)

Baseline `.planning/tmp/verify-README.json`: 147 checked / 141 passed / 6 failed.
Re-verification after the fix batch: **147 / 147 / 0** (same claim count, all pass).

## Re-verification method (worked end-to-end)
1. Read the baseline artifact FIRST — its `failures[]` list IS the fix checklist.
2. Map each failed claim to its README line, then read the CURRENT doc. Here the six
   fixes were in-place text swaps at lines 63, 82, 121, 138, and 284 (×2) — no reflow.
3. Verify each fixed claim FRESH against source anchors (quote exact strings, never paraphrase):
   - **L63 VITE_API_BASE_URL:** `frontend/src/api/client.ts` `const apiBase = import.meta.env.VITE_API_BASE_URL ?? ''`
     + `` fetch(`${apiBase}${url}`) ``; `chat.ts` streamMessage prefixes the same way;
     `frontend/vite.config.ts` `envDir: '..'` + `'/api'` proxy → `127.0.0.1:8000`.
     Fixed README says: set `VITE_API_BASE_URL=` (empty) for local dev, full backend
     origin in production. PASS.
   - **L82/121/284 candidate boundary:** `spoilerless/app/api/candidates.py`
     `_require_resolved_boundary` — 422 `INVALID_REQUEST` when `visible_until_order is None`,
     422 `INVALID_VISIBLE_UNTIL_ORDER` when the order is not a persisted episode; BOTH
     `list_candidates` and `get_candidate` declare
     `visible_until_order: int | None = Query(default=None, ge=1)` and call the helper
     before reading. "Requires a positive boundary validated against a persisted episode"
     is now exact. PASS.
   - **L138 rate limiting:** `spoilerless/app/services/rate_limit.py:23` imports
     `from pyrate_limiter import Duration, Limiter, Rate, RedisBucket, SingleBucketFactory`;
     `rg -n 'fastapi_limiter' spoilerless/ -g '*.py'` = 0 imports anywhere in app code;
     pyproject still declares `fastapi-limiter>=0.2.0` and pyrate-limiter lands in uv.lock
     transitively. Bounded DB-free proof:
     `unset PYTHONPATH; uv run python -c "import pyrate_limiter; from spoilerless.app.services.rate_limit import RateLimiter; ..."`
     → IMPORT_OK. PASS.
4. Re-confirm the previously-passing claims with a broad sweep (git remote
   `vinnipukh/hdgrafcehennemi.git`, config.py env fields, LLM_PROVIDERS tuple, jsdom lockfile
   engines, MAX_PATH_HOPS, ontology yamls, router prefixes, auth gating, docs table, .gitignore).
5. Write the artifact with the SAME `claims_checked` as the baseline (147): re-verification
   re-checks the same claim set. Invariants: `claims_passed + claims_failed == claims_checked`,
   `len(failures) == claims_failed`, `claims_checked > 0`.
6. Validate with a focused DB-free validator (temp `hermes-verify-readme.py` per the
   OS-temp pattern) asserting artifact invariants + quoted README strings + source anchors,
   then re-run the invariant check inline in a later turn as fresh evidence; delete the temp file.

## Anchors re-verified this session (do not re-derive)
- **jsdom 30.0.1 lockfile engines:** `"node": "^22.22.2 || ^24.15.0 || >=26.0.0"` — README's
  Node claim is exact; Vite's engines (`^22.13.0 || >=24.0.0`, lock lines ~72/98) are looser,
  so "jsdom requirement stricter than Vite's" holds.
- **LLM providers:** `LLM_PROVIDERS = ("gemini", "openai_compatible", "vllm", "ollama")` at
  `spoilerless/app/domain/settings.py:21`; vllm/ollama scaffold through OpenAICompatibleProvider
  (`services/chat.py`), gemini → GeminiProvider.
- **MAX_PATH_HOPS = 4** at `spoilerless/app/retrieval/tools.py:29`; path route field
  `max_hops: Field(default=MAX_PATH_HOPS, ge=1, le=MAX_PATH_HOPS)` (api/graph.py:164).
- **BYOK storage key** is `spoilerless:byok-llm-settings` (byok.ts:9), legacy
  `hdgraf:byok-llm-settings` read-compat fallback; headers X-LLM-Api-Key / X-LLM-Provider
  always, X-LLM-Base-URL / X-LLM-Model only when non-blank.
- **`.env.example` STILL ships `VITE_API_BASE_URL=/api` (line 13).** The README fix
  compensated with an explicit "set it empty locally" instruction, so no README claim is
  false — but the TEMPLATE itself still carries the production value. Future fix candidate:
  blank it in the template (or accept as an intentional prod-leaning template).

## Pitfall: feature-file existence checks must look in component subdirectories
`frontend/src/components/` is organized per-feature: `palette/CommandPalette.tsx`,
`series/SeriesDashboard.tsx`, `timeline/TimelineView.tsx`, plus `chat/`, `detail/`,
`episode/`, `layout/`, `graph/`, `settings/`, `share/`. A bare
`test -e frontend/src/components/CommandPalette.tsx` returns MISS and looks like a doc
failure — the component lives one level down. When a feature-name check misses, `ls`
the containing category directory before declaring the feature absent.
