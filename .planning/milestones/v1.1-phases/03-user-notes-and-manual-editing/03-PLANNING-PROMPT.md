# Phase 3 Backend Slice — Planning Prompt

Plan the locked Phase 3 backend slice using the decisions captured in the Phase 3 context.

The plan must cover:

1. Existing-state audit
- inspect current FastAPI routes, Pydantic schemas, Neo4j repository code, ontology validation, seed logic, tests, and OpenAPI output
- identify reusable code and compatibility risks
- do not redesign working modules without a demonstrated need

2. Notes
- series-scoped create, list/read, update, and hard-delete routes
- exactly one attachment target per note
- attachment targets limited to Character or Claim
- stable server-generated IDs and timestamps
- plain-text content validation
- validation that the target belongs to the selected series
- spoiler-safe visibility derived from the target
- notes must not weaken or bypass story visibility rules

3. Custom content
- series-scoped CRUD routes
- allowed node types: Character, Event, Location, Organization, Object
- allowed relationship types restricted to the existing ontology predicates
- create resources with origin: user
- update and delete only resources whose origin is user
- reject updates or deletion for canonical and candidate resources
- prevent arbitrary Neo4j labels, predicates, and unsupported properties
- preserve referential integrity during deletion

4. Spoiler visibility
- define the source of persisted visible_until_order
- define safe behavior when no visibility boundary exists
- derive write visibility server-side from the attachment target or selected episode
- apply visibility filtering to all story-sensitive reads
- prevent notes and custom content from leaking hidden characters, claims, or relationships
- document how visibility is calculated for nodes and relationships spanning multiple episodes

5. REST and OpenAPI contract
- explicit Pydantic request and response schemas
- consistent series-scoped route naming
- documented success and error responses
- one machine-readable error envelope
- response examples for ambiguous or important cases
- compatibility notes for existing frontend consumers
- no raw Neo4j records in public responses

6. Testing
- unit tests for schema and ontology validation
- API tests for all CRUD operations
- tests preventing canonical/candidate mutation
- tests for invalid attachment targets
- tests for invalid relationship predicates
- tests for cross-series references
- spoiler-boundary and hidden-resource tests
- deletion and referential-integrity tests
- OpenAPI contract assertions
- retain and run existing seed-idempotency tests

7. Scope boundaries
- do not modify frontend/
- do not implement authentication
- do not implement revision history, moderation, uploads, rich text, collaboration, LLM extraction, or ontology expansion
- do not commit .env or secrets

Break the work into small executable tasks with:
- exact files expected to change
- dependencies between tasks
- acceptance criteria
- verification commands
- suggested logical commit boundaries

Before finalizing the plan, explicitly list any technical assumption that could affect API compatibility or spoiler safety.
