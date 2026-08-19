# 11-08 Summary — P1 hardening (delimiter neutralization, bounded cache, ops cap, revert allowlist)

## Completed

- **Task 1 — Delimiter neutralization + output guard (SEC-LLM-004):**
  - `spoilerless/app/retrieval/context.py`: added `_neutralize(text)` escaping `<`/`>` and applied to `_entity_line` label, `_edge_line` type, `_claim_line` label/predicate, `_evidence_line` label/text, `_source_line` label/locator, `_note_line` content. Wrapping tags (`CONTEXT_DELIMITERS`) untouched (generated directly from `CONTEXT_SECTIONS`).
  - `spoilerless/app/retrieval/pipeline.py`: added `_neutralize_answer_delimiters(content)` escaping exact `<name>`/`</name>` for every `CONTEXT_SECTIONS` name, applied in `_finalize` after fallback selection before yielding `LLMEvent.done`. Added `max_length=20` to `ProposeChangesetInput.operations`.

- **Task 2 — Bounded viz cache + ops cap (SEC-DOS-005 / SEC-LLM-007):**
  - `spoilerless/app/cache/graph_cache.py`: added `FOCUS_SET_CAP=64`, `FOCUS_SET_TTL_SECONDS=3600`, and `_focus_capacity_allows(redis, series_id, focus_sig)` (sismember→scard→sadd+expire). `set_cached_visualization` now checks capacity when `focus_ids` present and skips SETEX when over cap (bounded per-series cardinality).
  - `spoilerless/app/retrieval/pipeline.py`: `ProposeChangesetInput.operations` capped at 20 (tighter than API 50). 21 ops → ValidationError → model-visible error; 20 ops allowed.

- **Task 3 — Revert allowlist + ownership fail-closed (SEC-GR-014 / SEC-AUTH-01) + QUAL-02 extraction:**
  - `spoilerless/app/revisions/__init__.py`: defined `_REVERT_LABEL_ALLOWLIST` (Claim, UserNote, ChangeSet, EvidenceFragment + CustomNodeType + NoteTargetType values). Added early guards before any f-string interpolation of `resource_type`/`target_type` (validates `resource_type` and `target_type` from before snapshot, 422 INVALID_ACTION on miss). Fixed ownership checks: `stored_owner != user_id` (removed `is not None` guard) for both UPDATED and DELETED paths, so `None` owner requires admin (fail-closed).
  - `spoilerless/app/services/change_set.py`: extracted `_propose_changeset_executor` logic into `ChangeSetService.propose_via_tool` (validates via `ProposeChangesetInput`, max 20, delegates to `propose`, returns model-visible error shapes). Added `ValidationError` import.
  - `spoilerless/app/retrieval/pipeline.py`: `_propose_changeset_executor` now thin-delegates to `ChangeSetService.propose_via_tool` (QUAL-02). Removed duplicated validation/service call.

## Verification

- Imports: `uv run python -c` confirmed `_neutralize`, `_neutralize_answer_delimiters`, focus cap, allowlist, and `propose_via_tool` all import without circular errors.
- Cap: `ProposeChangesetInput` rejects 21 ops (ValidationError) and accepts 20.
- Cache: `FOCUS_SET_CAP==64` present.
- Delimiters: `&lt;claims&gt;` escaped in context lines and answers; `"a < b"` untouched in answers.
- Unit tests: `uv run pytest test_prompt_injection (10 passed)`, `test_retrieval_pipeline (16 passed)` with dummy AURA env; full DB tests not run (Aura required).

## Residual / Follow-up

- Per-series Redis set `vizfocus:{series_id}` self-expires in 3600s; under sustained enumeration the attacker still pays fetch cost but not memory growth (bounded cardinality, not bounded compute).
- Pipeline `_neutralize_answer_delimiters` uses exact string replace; if new `CONTEXT_SECTIONS` added, guard automatically covers them (loop over tuple).
- Allowlist covers current enums; if new revision resource types added, allowlist must be extended.
