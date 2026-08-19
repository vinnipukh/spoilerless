# 08-01 deploy build traps (Vercel tsc -b, Render env) — verified 2026-08-04

## Frontend: `tsc -b` type-checks TEST files — plain `tsc --noEmit` does not

`npm run build` = `tsc -b && vite build` (Vercel runs exactly this). `tsc -b`
builds the referenced projects (tsconfig.app.json etc.) and type-checks TEST
files; plain `npx tsc --noEmit` from the frontend root loads only the solution
tsconfig (`files: []` + references) and does NOT check referenced projects —
so test-file type errors pass locally and fail the Vercel deploy.

Observed 08-01: `error TS18048: 'options' is possibly 'undefined'` at 5 sites
in `frontend/src/api/chat.test.ts`, build exited 2. Trigger pattern:

```ts
const [, options] = vi.mocked(globalThis.fetch).mock.calls[0]
expect(options.headers).not.toHaveProperty('X-LLM-Api-Key')  // TS18048
```

fetch's `init` is optional, so `options` is `RequestInit | undefined`.
Fix: `expect(options?.headers)...` — behavior-neutral (`expect(undefined)
.not.toHaveProperty(...)` still passes; the `toEqual` stream case always has
init present).

Rule: verify the EXACT Vercel command locally (`npm run build`), never a
looser substitute — a green `tsc --noEmit` is NOT evidence the deploy builds.
(Same class of trap as the vitest `NODE_ENV=test` requirement: the pipeline
that ships is the one to run.)

## Render: missing NEO4J_URI crashes startup with pydantic `Field required`

Deploy built fine, then uvicorn died at import: `ValidationError: 1 validation
error for Settings — neo4j_uri: Field required`. The env had
`NEO4J_USERNAME`/`NEO4J_PASSWORD`/`NEO4J_DATABASE` etc. but the URI was
forgotten — pydantic-settings treats a missing var as an error, not a blank.
Also: an `ALLOWED_EMAILS` value typed as literal `()` fails the list parse —
leave it empty for unrestricted (the field parses empty as "no allowlist").

Live health check that proves the whole chain (service + driver + Aura TLS +
certifi trust store): `GET https://<svc>.onrender.com/health` →
`{"status":"ok","database":"connected",...}`. Root path 404s by design.

## Deploy red-loop pattern (both platforms hit it same day)

1. Local: `tsc --noEmit` + vitest green → push → Vercel red (tsc -b).
2. Render: build green → start crash (missing env).
Fix each with the exact pipeline command / env completeness check, then
re-push — both platforms auto-redeploy on push (no manual re-trigger).
Commit test-infra fixes atomically (`fix(08-01): ...`) with the deploy in
mind; the commit message should name the failing pipeline step.
