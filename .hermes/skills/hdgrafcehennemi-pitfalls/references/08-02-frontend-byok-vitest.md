# Frontend BYOK (08-02 Task 2) — vitest patterns + Windows/MSYS host quirks

Committed 2026-08-04: `7665168` (feat) + `7e7e025` (test) + `d040eb4` (docs).
Feature: `frontend/src/lib/byok.ts`, SettingsPage localStorage-only rewrite,
chat.ts X-LLM-* header attachment + VITE_API_BASE_URL stream prefix,
types/settings.ts trimmed to BYOK-only, `frontend/src/api/settings.ts` deleted.

## BYOK contract facts (verified this session — reuse, don't re-derive)

- localStorage key: `hdgraf:byok-llm-settings`; shape
  `{provider: 'gemini'|'openai_compatible', api_key, base_url, model}` — all
  free-text fields trimmed on save (matches the backend's whitespace-only-key
  rejection).
- `getLLMHeaders()`: emits `X-LLM-Api-Key` always, `X-LLM-Base-URL` /
  `X-LLM-Model` only when non-blank; a missing/whitespace-only key returns `{}`.
  This is SAFE against the backend: `get_llm_provider` does
  `(x_llm_base_url or "").strip()` + truthiness, so a blank header is treated
  as absent and env fallback survives. Sending empty-string headers would also
  be harmless — omit blanks anyway ("when present" contract).
- Backend fixes the BYOK provider type to `openai_compatible`; there is NO
  X-LLM-Provider header.
- `frontend/src/api/client.ts` ignores `VITE_API_BASE_URL` entirely (plan 08-01
  owns it) — only `streamMessage`'s raw SSE fetch is prefixed
  (`import.meta.env.VITE_API_BASE_URL ?? ''`). `sendMessage` (via apiFetch) is
  intentionally NOT prefixed. `frontend/.env.example` still sets
  `VITE_API_BASE_URL=/api`, which WOULD double-prefix the stream URL once
  08-01 wires client.ts — 08-01 must normalize it to an origin (or empty).

## Vitest/jsdom patterns (all cost real time this session)

1. **`import.meta.env` values may be loaded from `.env.local` by vitest**
   (mode `test` loads `.env*` files; this repo's `.env.local` has
   `VITE_API_BASE_URL=/api`). Never hardcode expected URLs for code that reads
   env vars — compute the expectation with the SAME expression the source
   uses (`const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''`), so the
   test is robust whether or not the env file loads.
2. **jsdom localStorage persists across tests within one file** — always
   `localStorage.clear()` in `beforeEach` (and in App-level integration files,
   which already clear `sessionStorage`).
3. **Component switches from server-GET to localStorage** (SettingsPage
   rewrite): App-level tests that asserted server-populated values must seed
   the storage key before render; the fetchStub branch for the removed
   endpoint becomes dead code (harmless — leave or remove).
4. **Fetch-mock helpers used by multiple describes must be module scope.**
   A `function mockStreamResponse()` declared inside one describe's callback
   is invisible to sibling describes → ReferenceError at test time. Hoist to
   top level next to the other mock helpers.
5. **The no-network-save contract test**: `vi.stubGlobal('fetch', vi.fn())`
   + assert `not.toHaveBeenCalled()` after clicking Save proves the key never
   left the browser; assert the localStorage write separately via
   `JSON.parse(localStorage.getItem(key))`.
6. Full-suite run required even when the targeted run passes — App.test.tsx
   renders SettingsPage and broke on the server→localStorage switch; the
   targeted `src/components/settings src/api/chat.test.ts` run stayed green.

## Windows/MSYS host quirks (this repo's frontend work)

- **`search_files` tool fails on this host** with
  "Sistem belirtilen yolu bulamıyor" (path not found) for valid paths in both
  `C:\...` and `C:/...` forms — use `rg` via terminal instead (works).
- **`grep -En '[^\x00-\x7F]'` under Git-Bash/MSYS matches EVERY line** (the
  `\x00-\x7F` class is not interpreted by GNU grep -E there) — for the repo's
  no-non-ASCII-in-source-files check use `rg -n '[^\x00-\x7F]'` (flags only
  real non-ASCII; pre-existing box-drawing/em-dash comment lines will show —
  verify they are pre-existing before touching them).
- `read_file` accepts `C:\...` absolute paths; terminal commands need
  `/c/Users/...` or `cd` first.

## Git discipline note

- Verify `git ls-files <path>` BEFORE `git rm`. `frontend/src/api/settings.ts`
  existed only as an UNTRACKED working-tree file (HEAD's SettingsPage.tsx
  imported `@/api/settings` but git never tracked the module — a pre-existing
  broken import). Deleting an untracked file is invisible to `git status` and
  needs no commit; the rewrite that drops the import fixes the HEAD
  inconsistency.
- Targeted `git add <explicit paths>` only; never stage `.hermes/`; commit
  STATE/ROADMAP/SUMMARY as the final docs commit, never `.planning/config.json`.
