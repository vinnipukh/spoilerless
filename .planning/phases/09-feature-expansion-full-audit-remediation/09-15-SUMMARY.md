# 09-15 Summary: Documentation Alignment & Repo Hygiene

## Overview
Plan 09-15 aligned core documentation with shipped codebase capabilities and cleaned up repository hygiene:
1. **API & Contract Locked**:
   - `docs/API.md` and `docs/frontend-api-contract.md`: Updated OpenAPI inventory to **50 operations across 37 path templates**, including Phase 9 path finder (`POST /api/series/{series_id}/graph/path`), Markdown export (`GET /api/series/{series_id}/export`), and Share snapshot CRUD endpoints (`/api/share`).
   - `spoilerless/tests/test_frontend_contract_doc.py`: Updated contract lock test assertions to 50 operations / 37 path templates.
2. **Architecture & Roadmap Alignment**:
   - `docs/ARCHITECTURE.md`: Corrected ChangeSet capability documentation (`proposed_change_set`), updated Known Gaps to list only real gaps.
   - `docs/ROADMAP.md`: Updated Section 8 Known Gaps to reflect Phase 8/9 Google sign-in, HttpOnly session cookies, origin verification, and Admin RBAC.
3. **Repository Hygiene & Zero-Cost Compliance**:
   - `LICENSE`: Added MIT License file at repo root.
   - Removed PyCharm hello-world `main.py` template and Vite boilerplate `frontend/README.md`.
   - `data/dexter/seed/characters.json`: Removed third-party Wikia/Fandom `image_url` hotlinks, ensuring fallback to clean initial-based avatars without external tracking.

## Key Commits
- `1ddc650`: docs(09-15): regenerate API.md, correct ARCHITECTURE + ROADMAP, add MIT LICENSE, clean junk, drop hotlinks (DOCS-04/PROB-10/#21-25/#28)

## Verification
- `uv run pytest spoilerless/tests/test_frontend_contract_doc.py`: 3 passed in 0.73s
- `npx vitest run src/components/graph`: 5 test files, 37 passed
- `rg -c "wikia|nocookie" data/dexter/seed/characters.json`: 0 matches
- Root `LICENSE`: MIT License verified
