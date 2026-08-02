# Phase 6 — API Coverage Matrix: LLM Provider (OpenAI-compatible)

> Per the `ai-integration` plan:pre contribution — RAG-04 integrates an external LLM provider API as a
> first-class capability. Per research's primary recommendation (06-RESEARCH.md "Standard Stack" /
> "Architecture Patterns"), this phase implements the provider abstraction with `httpx.AsyncClient`
> directly against the OpenAI-compatible `/chat/completions` endpoint — **no new Python dependency**
> (`httpx` is already installed). No `openai` SDK, no `sse-starlette`. This keeps the capability surface
> to exactly what `/chat/completions` (streaming + tool-calling) exposes, not the full OpenAI product
> surface (embeddings, moderation, assistants, fine-tuning, etc.) — the matrix below is the subtraction
> record against that full surface, starting from full-coverage-by-default.

| capability | decision | reason |
|---|---|---|
| `chat_completion_non_streaming` | INTEGRATE | Required as the non-streaming fallback endpoint for tests/fallback (RAG-10, PRD §3) |
| `chat_completion_streaming` | INTEGRATE | Primary chat surface — incremental answer text over `/messages/stream` (RAG-10) |
| `tool_calling` (function calling) | INTEGRATE | Core mechanism for the allowlisted retrieval-tool loop (RAG-02, RAG-05) and ChangeSet proposal (RAG-11) |
| `structured_output_response_format` (native JSON-schema response_format mode) | OPT-OUT | ChangeSet/citation structure is enforced server-side via Pydantic validation of tool-call arguments, not the provider's native `response_format` mode — avoids a second parallel enforcement path alongside the ontology-allowlist validation already required by RAG-12 |
| `vision_image_input` | OPT-OUT | Not needed — all model context is text (graph data, evidence text, chat history); no image-understanding requirement anywhere in RAG-01..17 |
| `audio_speech` | OPT-OUT | Explicitly out of scope — voice chat is a named Deferred Idea in 06-CONTEXT.md / PRD §20 |
| `embeddings` | OPT-OUT | Not needed — retrieval uses allowlisted typed graph tool calls (RAG-02/RAG-03), not vector/embedding-based semantic search |
| `moderation` | OPT-OUT | Not needed yet — no content-moderation requirement stated in RAG-01..17 |
| `fine_tuning` | OPT-OUT | Not needed — no model customization is in scope for this phase |
| `batch_api` | OPT-OUT | Not needed — this is single-turn interactive chat only, no batch/offline processing use case |
| `assistants_threads_api` (provider-side stateful conversation/thread state) | OPT-OUT | Not needed — conversation state is persisted by this application in Neo4j via `ChatSession`/`ChatMessage` (RAG-09), never delegated to provider-side thread/assistant state |
| `model_listing` (`/models` discovery) | OPT-OUT | Not needed — `LLM_MODEL` is a fixed env-configured value; no runtime model-discovery/selection UI is in scope |
| `token_usage_logprobs` | OPT-OUT | Not needed yet — no token-cost tracking or explainability requirement in RAG-01..17 |

**Disposition summary:** 3 INTEGRATE (chat completion streaming + non-streaming + tool-calling — the exact
surface RAG-04/RAG-05/RAG-10/RAG-11 require), 10 OPT-OUT (all with a stated reason, none silently
dropped). No `[ASSUMED]`/`[SUS]` package installs are introduced by this phase (see 06-RESEARCH.md
"Package Legitimacy Audit" — `openai` and `sse-starlette` were both flagged `SUS` and are explicitly
**not used**, per research's primary recommendation).
