# Docs verifier process safety (2026-08-10)

## Trigger

Use this when running `gsd-docs-update` or fact-checking setup/testing/deployment docs in the HD Graf repository.

## Verified failure mode

Doc-verifier children interpreted “execute cheap bounded documented commands” too broadly:

- one ran `docker compose up -d neo4j`; Docker Desktop was unavailable and the command failed;
- another ran `uv run --project spoilerless uvicorn spoilerless.app.main:app --reload`, leaving a long-lived server/reloader on port 8000;
- stopping the tracked wrapper required a follow-up `curl`/`netstat` check because Windows wrappers can orphan the real child.

These processes were unnecessary for factual documentation verification.

## Safe verifier contract

Add these constraints to every docs verifier assignment:

1. **Do not start infrastructure or persistent services.** No `docker compose up`, database containers, Redis, Vite, Uvicorn, `--reload`, watchers, or background servers.
2. **Prefer static and parser-level evidence.** Read compose/render/Vite/config files; use `docker compose config`, import checks, CLI `--help`, OpenAPI generation in-process, or bounded unit/model tests.
3. **Do not run shared live-Neo4j suites.** Documentation verification should not mutate or depend on the shared graph.
4. **If a runtime smoke is indispensable, make it bounded and self-cleaning.** Use a foreground harness with a timeout and `finally` cleanup; never leave a reloader or background child.
5. **After any accidental server launch, stop the tracked process and verify the port is closed.** On Windows, wrapper termination alone is insufficient evidence.

## Prompt clause

```text
Process safety: do not run docker compose up, start Neo4j/Redis, launch Vite/Uvicorn, use --reload/watch mode, or create any persistent/background process. Verify startup claims via static config, imports, CLI help, in-process OpenAPI, or bounded DB-free tests. Do not run shared live-Neo4j suites.
```
