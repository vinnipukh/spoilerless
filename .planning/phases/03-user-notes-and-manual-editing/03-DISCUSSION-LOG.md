# Phase 3: User Notes and Manual Editing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-29
**Phase:** 3-user-notes-and-manual-editing
**Areas discussed:** Worktree scope, note lifecycle and attachment rules, custom-content boundaries, spoiler rules, REST/OpenAPI contract

---

## Worktree Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Backend slice of Phase 3 | Contract hardening plus note/custom-content APIs; UI remains pending in the frontend worktree | ✓ |
| Contract hardening only | Treat as pre-Phase-2 stabilization and do not create Phase 3 context | |
| Contract design only | Document Phase 3 APIs but defer implementation | |

**User's choice:** Backend slice of Phase 3.
**Notes:** The user explicitly prohibited frontend changes, authentication, automatic LLM extraction, and unrelated ontology expansion. Overall Phase 3 cannot be marked complete by this worktree alone.

---

## Note Lifecycle and Attachment Rules

| Option | Description | Selected |
|--------|-------------|----------|
| One Character or Claim | Exactly one target; strict NOTE-01 scope | ✓ |
| One exposed graph element | Any exposed node, edge, or claim | |
| Broader structural targets | Series, Episode, nodes, edges, or claims | |

**User's choice:** Exactly one `Character` or `Claim` target.
**Notes:** Notes require create/read/update/hard-delete lifecycle, stable server IDs, timestamps, plain-text content, and explicit rejection of malformed or ambiguous targets. Multi-target notes are excluded.

---

## Custom-Content Boundaries

| Option | Description | Selected |
|--------|-------------|----------|
| Narrative subset | Character/Event/Location/Organization/Object nodes; narrative and character relationships | ✓ |
| Nearly full ontology | Every ontology type except Revision | |
| Character-only | Character nodes and character predicates only | |

**User's choice:** The narrative subset.
**Notes:** Arbitrary labels, arbitrary relationship names, free-form Neo4j properties, and canonical overwrite/delete are forbidden. Mutations apply only to API-created `origin: user` resources.

---

## Content Discriminator

| Option | Description | Selected |
|--------|-------------|----------|
| Existing `origin` | Stabilize `canonical | candidate | user`; new content is `user` | ✓ |
| Rename canonical | Change `canonical` to `curated` | |
| Parallel flag | Add `is_custom` beside `origin` | |

**User's choice:** Preserve the existing `origin` field with `canonical | candidate | user`.
**Notes:** Avoids an unnecessary compatibility break and prevents competing classification fields.

---

## Spoiler Rules

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit read boundary, derived writes | Require persisted `visible_until_order` on story reads; derive write visibility from target/episode | ✓ |
| Client controls visibility | Client submits both read and write visibility | |
| Anonymous persisted progress | Add one local progress record and infer all boundaries | |

**User's choice:** Explicit read boundaries with server-derived write visibility.
**Notes:** Missing progress fails closed; no endpoint assumes all episodes are watched. Hidden targets, error messages, and aggregate metadata must not leak.

---

## Resource Identity

| Option | Description | Selected |
|--------|-------------|----------|
| Server-generated IDs | Namespaced stable IDs; clients cannot choose IDs | ✓ |
| Client IDs | Client supplies IDs in a validated `user:` namespace | |
| Idempotency keys | Optional client key plus server ID | |

**User's choice:** Server-generated namespaced IDs.
**Notes:** This strengthens canonical isolation and prevents collisions or overwrite attempts.

---

## REST Endpoint Organization

| Option | Description | Selected |
|--------|-------------|----------|
| Series-scoped resources | `/api/series/{series_id}/notes`, `/custom-nodes`, and `/custom-relationships` | ✓ |
| Top-level resources | `/api/notes` and `/api/custom-*` | |
| Mutation-only routes | Retrieve all user content solely through `/graph` | |

**User's choice:** Series-scoped CRUD resources.
**Notes:** Existing routes remain unchanged. Public operations use explicit Pydantic models, consistent statuses, a shared machine-readable error envelope, declared OpenAPI responses, and compatibility documentation.

---

## Claude's Discretion

- Internal Pydantic/module names and query organization following existing API/domain/graph boundaries.
- Conservative content-length limits and deterministic ordering.
- Transaction decomposition and whether user relationships persist directly or through an existing user-authored claim pattern, provided public behavior remains locked.

## Deferred Ideas

- React/Cytoscape integration in the separate frontend worktree.
- Revision history, restoration, and soft deletion in Phase 4.
- Candidate moderation/extraction preparation in Phase 5.
- Authentication, collaboration, rich text, uploads, automatic ingestion, LLM extraction/chat, and unrelated ontology expansion.
