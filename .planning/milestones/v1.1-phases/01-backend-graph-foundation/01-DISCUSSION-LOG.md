# Phase 1: Backend Graph Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-29
**Phase:** 01-backend-graph-foundation
**Areas discussed:** Backend boundary contract, Deterministic seed and ontology contract, Invalid graph-request behavior, Runtime acceptance evidence

---

## Backend Boundary Contract

### Spoiler boundary input
| Option | Selected |
|--------|----------|
| Validated `visible_until_order` query parameter | ✓ |
| Server-side persisted progress | |
| Persisted default with optional query override | |

**User's choice:** Validated `visible_until_order` query parameter — stateless and directly testable.

### Narrative relationship storage
| Option | Selected |
|--------|----------|
| Claim nodes derive narrative API edges | ✓ |
| Native narrative relationships plus linked Claim nodes | |
| Native relationships only with claim/evidence IDs as properties | |

**User's choice:** Claim nodes are the provenance-rich source of truth; structural topology remains native.

### Provenance response shape
| Option | Selected |
|--------|----------|
| Include claims, sources, and evidence in the graph response | ✓ |
| Separate claim/evidence detail endpoints | |
| Embed claim/evidence objects inside each edge | |

**User's choice:** Return complete filtered provenance as top-level collections.

### Neo4j unavailable at startup
| Option | Selected |
|--------|----------|
| Start degraded; `/health` returns 503 | ✓ |
| Fail FastAPI startup | |
| Start degraded; `/health` always returns 200 | |

**User's choice:** Keep FastAPI/Swagger available in degraded mode and report real health with 503.

---

## Deterministic Seed and Ontology Contract

### Ontology enforcement
| Option | Selected |
|--------|----------|
| Ontology YAML is the authoritative allowlist | ✓ |
| Ontology YAML is documentation only | |
| Freeze only node types | |

**User's choice:** Validate seed values and explicitly document/version ontology changes.

### Stable IDs
| Option | Selected |
|--------|----------|
| Readable deterministic namespaced IDs | ✓ |
| Deterministic hash IDs | |
| Random UUIDs persisted in fixtures | |

**User's choice:** Human-readable namespaced IDs for every graph-visible seeded record.

### Reseed behavior
| Option | Selected |
|--------|----------|
| Seed-owned upsert without destructive reset | ✓ |
| Create-only seed | |
| Reset all Prototype v0 graph data | |

**User's choice:** Converge seed-owned records/relationships while preserving user-origin content.

### Evidence content
| Option | Selected |
|--------|----------|
| Short excerpt or faithful paraphrase plus precise episode locator | ✓ |
| Exact dialogue excerpts only | |
| Locator and source metadata only | |

**User's choice:** Concise evidence with precise locator and provenance metadata; no long transcript dumps.

---

## Invalid Graph-Request Behavior

### Boundary validation
| Option | Selected |
|--------|----------|
| Require a persisted episode order for the series | ✓ |
| Accept any integer through the maximum | |
| Clamp to nearest valid order | |

**User's choice:** The requested boundary must correspond to a persisted Episode for that series.

### Validation status codes
| Option | Selected |
|--------|----------|
| 404 unknown series; 422 invalid boundary | ✓ |
| 404 for both | |
| 400 for all validation failures | |

**User's choice:** Distinguish lookup failure from input validation.

### Database error mapping
| Option | Selected |
|--------|----------|
| Sanitized 503 from all database-backed endpoints | ✓ |
| Generic 500 | |
| Propagated driver exceptions | |

**User's choice:** Central sanitized 503 mapping with no sensitive implementation details.

### Error response contract
| Option | Selected |
|--------|----------|
| Stable error code plus safe message | ✓ |
| FastAPI string detail only | |
| HTTP status only | |

**User's choice:** Stable `detail.code` and safe `detail.message`; frontend owns localized presentation.

---

## Runtime Acceptance Evidence

### Test balance
| Option | Selected |
|--------|----------|
| Fast isolated tests plus focused live-Neo4j integration tests | ✓ |
| Live-Neo4j integration tests only | |
| Mocked/unit tests only | |

**User's choice:** Use both layers so response/lifecycle behavior stays fast while real Cypher is proven.

### Idempotency proof
| Option | Selected |
|--------|----------|
| Double-seed plus exact graph invariants | ✓ |
| Double-seed and compare total node count only | |
| Infer idempotency from `MERGE` | |

**User's choice:** Run twice and prove exact IDs, counts, uniqueness, properties, and response stability.

### Spoiler-leak proof
| Option | Selected |
|--------|----------|
| Boundary 1–3 future-sentinel assertions over full JSON | ✓ |
| Check only node visibility fields | |
| Test one future node ID at S01E01 | |

**User's choice:** Assert every serialized surface, including nested provenance and count signals.

### Local-stack acceptance
| Option | Selected |
|--------|----------|
| One repeatable smoke command plus automated tests | ✓ |
| Separate manual browser/curl steps only | |
| Automated tests only | |

**User's choice:** Reproducible local smoke execution with captured output.

---

## Claude's Discretion

- Exact small-module names and boundaries.
- Exact curated graph breadth, provided all three episode boundaries are meaningfully exercised.
- Safe backend message wording, additional justified indexes, and locator type chosen per evidence source.

## Deferred Ideas

- Server-side persisted watch progress.
- User notes/manual graph editing, revisions/revert, and extraction preparation remain later delivery phases.
- Authentication, GraphQL, vector search, GraphRAG, scraping, PDF parsing, external ingestion, extraction models, and LLM integration remain out of Phase 1.
