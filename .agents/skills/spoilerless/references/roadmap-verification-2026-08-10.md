# `docs/ROADMAP.md` accuracy review — 2026-08-10

## Result

- Artifact: `.planning/tmp/verify-ROADMAP.json`
- Claims: 197 checked, 180 passed, 17 failed.
- The artifact passed the standard verification-artifact validator and a targeted one-test pytest schema/invariant check.

## Durable audit pattern

For a hand-written roadmap, classify each statement before judging it:

1. **Historical scope/evidence** — preserve dated/original-target claims unless the historical record itself is wrong.
2. **Current/completed status** — verify against live routes, dependencies, repository predicates, tests, manifests, and UI reachability.
3. **Future/backlog intent** — absence is not a failure, but a future item is stale when the capability already shipped.
4. **Production-readiness qualification** — repository deployment manifests do not prove a live production deployment, but they do falsify categorical claims such as “no deployment architecture is configured.”

Roadmaps repeat the same status in principles, milestone headings, acceptance obligations, known gaps, and future backlog. Audit every occurrence and emit one failure per stale occurrence. Within one sentence, split independently false assertions (for example candidate list vs candidate detail; deployment architecture vs CI workflow).

## Live facts that invalidated this roadmap

### Candidate read boundaries are shipped

`spoilerless/app/api/candidates.py`:

- `_require_resolved_boundary` rejects omitted boundaries and unresolved episode orders with 422.
- Candidate list and detail both call the resolver and pass `visible_until_order` to repository reads.
- Detail treats above-boundary claims as missing.

Therefore all present-tense/future claims that list filtering is optional, detail has no boundary, or candidate boundary hardening remains future are stale.

### Mutation auth/ownership is shipped

- `api/user_content.py`: all note/custom-node/custom-relationship creates, updates, and deletes require `CurrentUserDependency`; update/delete paths thread `actor_id` and `is_admin` into owner-scoped repository queries.
- `repository/user_content.py`: owner predicates use forms such as `($is_admin = true OR node.user_id = $user_id)`.
- `api/revisions.py`: revert requires `CurrentUserDependency` and checks stored/snapshot ownership where present.
- `api/candidates.py`: ingest requires an authenticated user; approve/reject/edit require admin.
- `api/settings.py`: settings routes require admin.
- Tests cover anonymous 401, cross-owner 403, and admin bypass.

Thus blanket claims that authenticated ownership/authorization for these mutation families remains future are stale. If documenting residual gaps, name the exact read/privacy or legacy-ownerless branch rather than restoring the old blanket statement.

### Deployment and CI exist, with limitations

- `render.yaml` declares the FastAPI backend service and build/start commands.
- `frontend/vercel.json` declares SPA rewrites.
- `.github/workflows/ci.yml` runs on pull requests, provisions a dedicated Neo4j service, seeds it, runs pytest, checks DB residue, and runs frontend build/lint/audit.
- `.github/workflows/release.yml` is only a staged-promotion **skeleton**: its “verify CI gate” step echoes rather than querying checks, and its declared `contents: read` permission cannot push a tag.

Accurate wording: deployment architecture/config and PR CI are repository-declared; operator/platform production state and release enforcement may remain incomplete. Do not collapse these into “no deployment architecture or CI.”

## Artifact discipline

Use exact JSON keys:

- `doc_path`
- `claims_checked`
- `claims_passed`
- `claims_failed`
- `failures`

Each failure has `line`, `claim`, `expected`, `actual`; require positive checked count, `passed + failed = checked`, and `len(failures) = failed`. Validate with `project-documentation/scripts/validate-verification-artifact.py`. If a fresh canonical test signal is required, create one temporary OS-temp pytest file that reads only the final artifact, run that single test, then delete it; do not run the live-Neo4j application suite for a documentation artifact.