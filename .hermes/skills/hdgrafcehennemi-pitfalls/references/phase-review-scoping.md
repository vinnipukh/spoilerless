# Phase code-review scoping — hdgrafcehennemi

Learned during the Phase 9 review (2026-08-13, 149 files scoped from 18 plans).
Applies to `/gsd-code-review`-style phase reviews where the workflow scopes files
from SUMMARY.md and you must verify claims against real code.

## SUMMARY.md format heterogeneity (phase 09)

The 18 phase-09 summaries use THREE different shapes. The workflow's
frontmatter-only extractor (`key-files.created/modified` in YAML frontmatter)
recovered only 4 files (09-02) — 14 plans would have been silently dropped:

1. **YAML frontmatter with key-files** — only 09-02 had parseable entries.
2. **`## Artifacts Produced / Modified` bullet lists** — 09-11, 09-12 (parseable).
3. **Prose-only** — 09-01, 09-03..09-10 mention files as backticked prose;
   09-13/09-14/09-16 use **bare filenames without directory prefixes**
   (e.g. `` `BacklinksTab.tsx` ``), so an existence-check extractor misses
   them — resolve manually against known `frontend/src/...` paths.
4. **09-16** has zero source files (remote push / CI verification only) — don't
   force a scope for it.

Extraction recipe that worked (node, run from repo root):
- scan BOTH backtick-quoted paths anywhere in the file AND `- ` bullet lines;
- strip backticks / quotes / trailing `(…)` / `— description` tails; reject
  tokens containing spaces or `..`;
- require existing-on-disk (`fs.existsSync`); keep known extensionless build
  files (Dockerfile, Makefile);
- supplement manually for bare-filename summaries (09-13/09-14).
- Always cross-check the resulting scope against the phase git diff (#2666) so
  a partial SUMMARY parse can't silently shrink the review.

## Phase-commit grep pitfall (diff base)

The workflow's Tier-3 diff-base grep `git log --grep="[Pp]hase NN\b"` returns
NOTHING on this repo: commits are tagged `feat(09-11): ...` / `docs(09): ...`,
never "Phase 09". Use `git log --all --grep="09-"` (or each SUMMARY's commit
table) to find the span. CRITICAL: the diff endpoint must be the LAST
`NN-`-tagged commit (phase 09: `51d69c5`), NOT `HEAD` — HEAD includes
post-phase commits (`67ae4de`, `a430263`, ...) that pollute the scope
(280 files vs ~150 actually in-phase).

## Verification pattern that caught real bugs

Never trust SUMMARY bullet claims; grep the code. Real catches during phase 09:
- `main.py:139` calls `logger.exception(...)` but the module defines only
  `log = logging.getLogger(__name__)` → NameError on first DB error kills the
  background session/share sweep loop permanently (SUMMARY claimed
  "per-iteration exception tolerance"). Grep `\blogger\b` vs `\blog\b` when a
  module mixes the two names.
- `core/errors.py` comment claims `ClientError` is "deliberately EXCLUDED"
  from the 503 handler, but `issubclass(ClientError, Neo4jError)` is True in
  neo4j 6.x → the Neo4jError handler still masks invalid-Cypher bugs as 503.
  Verify subclass relationships before trusting "excluded" comments.
- `api/share.py` create_share_link accepted a client-chosen
  `visible_until_order` with no clamp to the creator's persisted progress —
  compare sibling routes (`_resolve_effective_boundary` in api/graph.py) when
  a new route claims to reuse a boundary model.
- Docstring/code disagreement on error codes: the 09-05 uppercase sweep is the
  source of truth (`^[A-Z][A-Z0-9_]*$`, registry in `core/errors.py`); stale
  docstrings citing lowercase codes are Info-level findings, not code bugs.
