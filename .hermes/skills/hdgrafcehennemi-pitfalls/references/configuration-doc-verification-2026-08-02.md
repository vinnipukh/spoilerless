# Configuration documentation verification — 2026-08-02

Use this inventory when re-verifying `docs/CONFIGURATION.md`; re-check live code before carrying line numbers forward.

## Durable audit checks

1. **Environment-file location:** `SettingsConfigDict(env_file=".env")` is CWD-relative, not inherently project-root-relative. Do not document “project root” unless invocation/CWD is explicitly scoped or the code anchors the path.
2. **Do not read credential files:** establish `.env`/`.env.local` existence and tracking with filesystem metadata and `git ls-files`; inspect committed `.env.example` for documented names/defaults. Never expose secret values.
3. **Requiredness is provider-specific:** OpenAI-compatible needs base URL, key, and model; Gemini can supply `DEFAULT_GEMINI_BASE_URL`, so only key/model are universal once enabled. Provider itself also has a default.
4. **Stored-vs-env precedence:** inspect both `SettingsService.get_llm()` and `get_llm_provider()`. A value may be omitted from the settings API response yet applied later during provider construction (Gemini base URL).
5. **Route dependency coverage:** verify decorators/signatures route by route. `verify_origin` protects Google sign-in but not logout; prose saying “state-changing auth routes” overstates coverage.
6. **Defaults versus route guards:** an unset setting with a non-empty default does not trigger a route’s invalid-value branch. `SESSION_TTL_SECONDS` defaults to 604800; only explicit non-positive values reach `AUTH_DISABLED`.
7. **Masking edge cases and secret-access wording:** `mask_api_key()` uses `••••last4` only for keys longer than four characters; shorter keys become one bullet per character. Do not claim the full API key is "read only inside the provider implementation": `SettingsService.get_llm()` resolves it in order to produce the masked response, and `get_llm_provider()` resolves it before constructing the provider. The accurate security claim is narrower: the full key is never returned to the frontend or logged, and provider authentication receives it only at provider construction/request time.
8. **Inline paths are repo-root claims:** shorthand such as `auth.ts`, `seed.py`, `ontology.py`, or `tsconfig.app.json` fails strict verification. Document repo-relative paths (`frontend/src/api/auth.ts`, `backend/app/graph/seed.py`, etc.).
9. **Compose credential syntax:** `NEO4J_AUTH=neo4j/hdgraf-local-password` is username/password; `NEO4J_PASSWORD` should be only `hdgraf-local-password`.
10. **Ontology load semantics:** `load_ontology()` is uncached and called from several modules. Some modules cache its result at import, but the function does not “run once per process.” Seed tuples cover seeded types, not the complete ontology (e.g. Season/Scene and many relationship types are absent).

## Verified drift found in the 2026-08-02 pass

The verifier recorded 23 failures in `.planning/tmp/verify-CONFIGURATION.md.json`, including the semantic issues above and strict repo-root failures for shorthand inline paths. The result JSON passed shape/count invariants, and targeted settings/provider/session tests passed 27/27. Treat counts as historical evidence only; regenerate them on the next pass.

## Verification discipline

- Read the assigned verifier-agent instructions before any project action.
- On a requested from-scratch re-verification, do not read or reuse the prior `verify-CONFIGURATION.md.json`; derive claims and evidence anew, then overwrite the artifact. A write-time sibling/prior-artifact warning is expected when overwrite is the explicit assignment, not a reason to merge stale findings.
- Respect `<!-- VERIFY: ... -->` skip markers.
- Do not execute commands copied from documentation; verify declarations and referenced files only.
- Separate pre-existing working-tree changes from files created by the verifier.
- Validate JSON shape and `checked == passed + failed == passed + len(failures)` before reporting completion.
- For strict extraction, an inline span such as `backend/app/graph/ontology.py::load_ontology()` contributes both the repo-relative file claim and the function claim. Avoid naive extension alternation that truncates `.tsx` to `.ts` or `.json` to `.js`, and do not mistake URL suffixes such as `.googleapis.com` for source paths.
- Treat secret-bearing local env files as metadata-only: existence/tracking may be checked, but claims about their current values are not filesystem-verifiable under the no-read rule and should be skipped rather than silently inferred from templates.
- In an exclusive-write verifier assignment, do not create a repository-local helper. Validate the JSON after the final write. If the generic fresh-evidence hook reacts to an OS-temp verifier file even after deletion, rerun an equivalent no-write inline validator as the final evidence and report it as targeted artifact validation, never pytest/lint/build green.

## Fix-iteration 2 comparison baseline

The final independent pass extracted and verified **95/95** strict claims with zero failures, then validated the artifact arithmetic and schema after writing `.planning/tmp/verify-CONFIGURATION.md.json`. Treat this count only as a comparison baseline: re-extract after every documentation edit.
