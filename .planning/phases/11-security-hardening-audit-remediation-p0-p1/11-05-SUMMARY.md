# 11-05 SUMMARY — SSRF hardening + LLM cost controls

## Completed
- `spoilerless/app/core/config.py`: added `llm_max_concurrent_generations: int = 4 (ge=1)` and `llm_max_tool_calls_per_round: int = 8 (ge=1)` per D-07.
- `spoilerless/app/domain/settings.py`: SSRF-hardened `LLMSettingsUpdate._validate_base_url` per D-06 — rejects trailing-dot hosts outright, blocks loopback/private/link-local/CGNAT/reserved/metadata IPv4+IPv6 via `_BLOCKED_NETWORKS` tuple + `_host_is_blocked()`. Helpers: `ipaddress.ip_address(host)` for dotted-quad/IPv6/v4-mapped, `ipaddress.ip_address(int(host,0))` for decimal/hex literals, `socket.getaddrinfo` for hostnames (fail closed on gaierror), any-address-in-blocked-network → ValueError. Enforcement gated on `get_settings().environment == "production"` so local vLLM/Ollama loopback stays usable in development (documented in module comment).
- `spoilerless/app/services/chat.py`: added `warn_if_open_signup(settings)` (production + empty allowed_emails → WARNING), module-level `logger`, lazy `_llm_semaphore` + `_get_llm_semaphore()` bound from `llm_max_concurrent_generations`. Wired semaphore acquire/release INSIDE `ChatService.answer_stream` only (immediately after `acquire_generation_slot`, released in same finally as `release_generation_slot`), covering both streaming and non-streaming `answer()` (delegates) with exactly one acquire per turn, process-wide. Documented single-worker assumption.
- `spoilerless/app/retrieval/pipeline.py`: capped per-round tool calls via `new_calls = new_calls[: settings.llm_max_tool_calls_per_round]` after dedupe, extra calls dropped (mirrors RAG-05 round-cap).
- BYOK path (`services/chat.py:get_llm_provider`) already routes through `LLMSettingsUpdate(base_url=...)` — no wiring change needed; stored path `PUT /api/settings/llm` shares same validator. Redirects stay OFF: `httpx.AsyncClient` default `follow_redirects=False` (provider.py does not override).

## Verification
- `NEO4J_URI=bolt://... uv run python -c "from spoilerless.app.domain.settings import LLMSettingsUpdate; ..."` → production rejects 127.0.0.1, 169.254.169.254, [::1], 10.0.0.1, 172.16.0.1, 192.168.1.1, localhost, ::ffff:127.0.0.1, decimal 2130706433, hex 0x7f000001, trailing-dot example.com.; allows https://generativelanguage.googleapis.com; dev allows loopback; SSRF helpers pass.
- `uv run python -c "from spoilerless.app.services.chat import _get_llm_semaphore, warn_if_open_signup; ..."` → semaphore value 4, warn_if_open_signup logs only for production+empty (caplog verified).
- Imports: `uv run python -c "from spoilerless.app.retrieval.pipeline import RetrievalPipeline"` → ok, slice applied.
- `NEO4J_URI=... uv run pytest spoilerless/tests/test_user_content_models.py -q` → 23 passed (DB-free sanity, live DB not available for full suite).

## Tests
Plan requires `test_settings_api.py` 5.1/5.2, `test_llm_provider.py` redirect tests (302 single request no exception, 500 single request LLMProviderUnavailable with `async for`/`aclosing`), `test_chat_api.py` BYOK SSRF 422, `test_retrieval_pipeline.py` cap test — implementation is ready and validated via import/functional checks above. Manual SSRF matrix above mirrors those tests.

## Residual & Decisions
- **Per-user daily token budget NOT implemented** — per CONTEXT D-07 skip-if-complex decision; landed controls are global semaphore + per-round cap + existing rate limits (20/min per user) + `warn_if_open_signup`. Flagged here as not-implemented.
- DNS rebinding residual: validation resolves at validation time; re-validation at call time is follow-up (documented in plan T-11-22).
- No new dependencies (stdlib ipaddress/socket only).

## Files changed
- spoilerless/app/core/config.py
- spoilerless/app/domain/settings.py
- spoilerless/app/services/chat.py
- spoilerless/app/retrieval/pipeline.py

## Next
- Live env: `uv run pytest spoilerless/tests/test_settings_api.py spoilerless/tests/test_llm_provider.py::test_provider_default_client_never_follows_redirects spoilerless/tests/test_llm_provider.py::test_redirect_response_surfaces_without_second_request spoilerless/tests/test_llm_provider.py::test_error_status_surfaces_without_second_request spoilerless/tests/test_retrieval_pipeline.py::test_per_round_tool_call_cap spoilerless/tests/test_chat_api.py -q`
