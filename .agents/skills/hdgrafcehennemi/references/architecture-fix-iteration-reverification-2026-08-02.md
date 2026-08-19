# Architecture doc fix-iteration reverification — 2026-08-02

Use this reference when adversarially re-verifying `docs/ARCHITECTURE.md`. Re-check the live doc and source first; prior counts are comparison aids only.

## High-yield checks that escaped earlier verification

1. **Provider protocol wording**
   - `OpenAICompatibleProvider` uses `/chat/completions`.
   - `GeminiProvider` is a separate implementation using `/v1beta/models/{model}:streamGenerateContent?alt=sse`.
   - Do not describe Gemini as a chat-completions endpoint or collapse the two concrete implementations into one.

2. **Frontend routing and layout exceptions**
   - `GraphCanvas` does not re-run layout on every graph-object change: it skips `runLayout` while `focusedElementIds` or a reveal target is active.
   - Edge routing is not a two-way structural-vs-claim-backed split. Claim-less user-origin edges go to `DetailPanel`; claim-less non-user edges go to `StructuralEdgeCard`.

3. **Example IDs must match seed metadata**
   - The seeded Dexter series ID is `series_dexter`, not `series:dexter`.
   - Check repeated IDs across a whole flow block; one bad example may appear in several calls.

4. **Protected ChangeSet substitution is type-limited**
   - `_note_target_type` maps only `Character` and `Claim`.
   - Other protected canonical/candidate target labels raise `ChangeSetValidationError`; they do not receive a transparent `create_note` substitution.

5. **Blank secret semantics include whitespace**
   - `SettingsService.update_llm` preserves `None` and `""`, but a whitespace-only `api_key` is truthy and is persisted because the service does not strip it.
   - Avoid saying every “blank” key preserves the old key unless whitespace is explicitly excluded or fixed in code.

6. **`claim_id: null` is not structural-only**
   - `VISIBLE_USER_RELATIONSHIPS_QUERY` projects user-authored `Claim` nodes as edges with `claim_id: null`.
   - Therefore, not every visible claim-derived edge carries `claim_id`, and null does not uniquely identify structural edges.

## Verification discipline

- Treat prose summaries, diagrams, design-decision tables, and example flow IDs as claims; do not verify only explicit paths/endpoints.
- Re-read implementation guards and exception branches. Absolute words such as “every,” “only,” and “always” often hide the drift.
- Keep the verifier read-only except for `.planning/tmp/verify-ARCHITECTURE.md.json`.
- Validate artifact arithmetic and schema with an OS-temp `hermes-verify-*` script, then delete it. If a generic hook asks for pytest/lint/build, report that runtime suites are inapplicable to the filesystem-only verifier role; rerun the targeted artifact validator rather than violating scope.

## Historical comparison baseline

The final fix-iteration-2 pass checked 265 claims and reported 257 passed / 8 failed. Always re-extract after edits; do not reuse these counts as evidence.
