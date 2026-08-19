# Phase planning without implementation

Use when user restricts work to docs, context, and planning.

## Hard boundary

1. Disable GSD auto chaining before planning:
   - `workflow.auto_advance = false`
   - `workflow._auto_chain_active = false` when present.
2. Limit writes to `.planning/` and requested documentation.
3. Before commit, run `git status --short -- spoilerless frontend scripts`; any output requires investigation. Do not stage source changes.
4. Mark state explicitly: planning complete; implementation not started; execution requires separate authorization.

## Recover interrupted plan/check loops

- Inspect all existing `*-PLAN.md` files before restarting generation. Preserve good artifacts; perform targeted revisions.
- Re-run independent gates after edits:
  - every plan: `gsd-tools verify plan-structure <plan>`;
  - every plan: `gsd-tools verify references <plan>`;
  - phase: `gsd-tools query check decision-coverage-plan <phase-dir> <context>`;
  - repository: `gsd-tools validate consistency`, `gsd-tools roadmap validate`;
  - `git diff --check` on planning scope.
- `verify references` treats `@path</context>` as one malformed path. Put `</context>` on its own line.
- Confirm all roadmap requirement IDs appear in plan frontmatter and all dependency IDs exist.

## HD Graf test-plan safety

Do not plan full backend regression against shared AuraDB or developer Neo4j data. Specify a future test runner that:

- provisions a uniquely named Neo4j container and ephemeral volume;
- exports both `NEO4J_*` and lowercase `aura_*` values because `AliasChoices("aura_*", "neo4j_*")` gives `aura_*` precedence;
- rejects Aura/remote/shared targets and the developer container/volume;
- clears ambient `PYTHONPATH`;
- cleans container and volume in `finally` on success or failure;
- has mock-driven tests proving rejection and cleanup.

Automated GraphRAG validation uses FakeLLM. Manual BYOK UAT uses only an operator-approved zero-cost provider; otherwise record provider call as operator-touch blocked. Never record keys.

## Adversarial revision re-checks

When re-checking a revised planning package after named findings, verify the fixes as executable contracts rather than keyword presence:

- Extract every `<automated>` command and require fail-fast composition (`&&`), not `;`, for dependent multi-command gates. Do not treat a trailing success message as proof.
- Cross-check planned symbols, paths, test names, dependency versions, configuration alias precedence, and runner inventory against the live repository. For layout work, use the actual exported helper name (currently `layoutOptionsFor`).
- For each new API, require an exact method/path/query/response/error contract plus same-task OpenAPI inventory, contract-test, and frontend-contract-document updates. Check cumulative operation/template counts when routes land in different plans.
- Audit cache keys against every request input that can change a response. Series/order/view/version/epoch/user is insufficient when focus IDs, expansion node, expansion key, limit, filters, or other request-specific inputs affect output; require normalized key dimensions or an explicit cache bypass.
- A Redis epoch plan must define default/read failure behavior, atomic increment, all content-changing invalidation call sites, race semantics, stale-key separation/deletion, and tests.
- A coverage parser must have a self-contained authoritative inventory. Saying “inventories listed above/already listed” is invalid unless the IDs are literally present in the executable plan or an explicitly named canonical source. Require delimited-block-only parsing, exact header handling, separator skipping, duplicate/missing/extra/malformed/empty-field rejection, marker cardinality tests, and unrelated-table tests.
- Verify every current and planned `test_*.py` appears exactly once in the full backend runner. When prior baseline reds are assigned, name the exact owning files and require fixes rather than whitelisting or weakened assertions.
- Check every validation threat reference resolves to an actual plan threat row, all required frontmatter keys exist, and all roadmap requirement IDs occur in plan frontmatter.
- For pinned dependencies, query the registry for the exact runtime and declaration versions and ensure both manifest and lockfile are planned.

A revision passes only when no remaining BLOCKER/WARNING issue survives these checks; keep read-only reviews read-only.

## Completion evidence

Report plan count, dependency waves, requirement coverage, decision coverage, structural/reference validation, source-tree cleanliness, commit, and explicit `implementation started: no`.
