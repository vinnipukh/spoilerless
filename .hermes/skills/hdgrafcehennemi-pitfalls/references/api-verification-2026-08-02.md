# Adversarial API.md verification findings — 2026-08-02

Use this as a regression checklist when verifying or regenerating `docs/API.md`. Re-check source before carrying any line numbers forward.

## Verification method that worked

1. Generate `app.openapi()` without starting a server and compare the documentation inventory as exact `(method, path)` pairs, including duplicate detection and separate path-template/operation counts.
2. Treat OpenAPI as inventory/schema evidence only. Read route dependencies, services, repositories, and Cypher for authentication, persistence, origin/CSRF behavior, SSE terminal frames, concurrency limits, canonical/candidate protections, and settings/provider resolution.
3. Distinguish response typing from request validation. A `dict` response model does not weaken a typed request model's `extra='forbid'` behavior.
4. For security claims, inspect every branch, not only the common branch. A guard in `Updated` does not prove the same invariant in `Deleted`.
5. For "effective settings" claims, follow values through both the settings response service and runtime provider construction; defaults applied only during provider creation are not present in the settings API response.
6. Probe normalization semantics adversarially: `None`, `''`, and whitespace-only strings are distinct unless code strips them.
7. Validate the result artifact structurally: checked = passed + failed, failed = `len(failures)`, and each failure has exactly `line`, `claim`, `expected`, and `actual`.

## Drift found in this verification

- Origin/Referer: `verify_origin` allows `candidate is None`; Referer parsing exceptions (for example an invalid port) set `candidate=None`, so a present malformed Referer can bypass the check.
- Strict request models: API prose tied unknown-field rejection to untyped `dict` responses, but response typing is unrelated; candidate request models still forbid extras.
- Revision protection: `revert_revision` checks canonical/candidate origin only in the `Updated` branch. The `Deleted` branch recreates the before snapshot without an origin check.
- LLM settings: `SettingsService.get_llm()` returns stored/env `base_url` or `None`; the Gemini default is applied later in `get_llm_provider`, so the GET settings response does not always expose the runtime-effective URL.
- API-key retention: `None` and `''` retain the stored key, but whitespace-only strings are truthy and are persisted because `update_llm` does not strip `api_key`.

These are documentation-verification findings, not authorization to modify source or docs during a verifier run. The verifier writes only `.planning/tmp/verify-*.json`.
