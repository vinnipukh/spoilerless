# `docs/TESTING.md` adversarial verification (2026-08-02)

Use this reference when regenerating or re-verifying the testing guide after a fix iteration.

## Evidence procedure

1. Re-read `docs/TESTING.md` from disk; do not reuse the prior verifier artifact or prior pass count.
2. Verify the root `pyproject.toml`, `frontend/package.json`, `backend/tests/conftest.py`, `frontend/vite.config.ts`, and `frontend/src/test/setup.ts` directly.
3. Walk `backend/tests/test_*.py` and `frontend/src/**/*.test.ts{,x}` statically to confirm file-layout, helper/fake, marker, and frontend-testing claims. Exclude `.git`, `node_modules`, virtual environments, Neo4j data directories, and credential-bearing `.env*` files.
4. Confirm command claims by checking script/dependency/file/function existence only. The doc-verifier contract forbids executing commands copied from the document, so do not run pytest, Vitest, npm install, Docker Compose, or `uv sync` as part of this artifact-only verification.
5. Check CI claims by scanning for common workflow files/directories, not only `.github/workflows/`.
6. Keep an atomic claim ledger while inspecting so `claims_checked` is reproducible. Count repeated claims at each occurrence; exclude behavioral/runtime claims that filesystem evidence cannot establish rather than inventing evidence.
7. Write only `.planning/tmp/verify-TESTING.md.json`; do not edit the documentation or source.
8. After writing, create a `hermes-verify-*` Python file in the OS temp directory, validate exact keys, positive checked count, arithmetic (`passed + failed == checked`), and `failed == len(failures)`, run it, then delete it. If Hermes repeats its freshness warning, rerun this focused temp validator; do not substitute a project test suite or claim suite green.

## Fix-iteration-1 result

The from-scratch pass checked 121 atomic claims: 121 passed, 0 failed. The result artifact used:

```json
{
  "doc_path": "docs/TESTING.md",
  "claims_checked": 121,
  "claims_passed": 121,
  "claims_failed": 0,
  "failures": []
}
```

Treat this count as historical evidence only. Re-extract and recount after any document change.