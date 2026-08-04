"""Settings domain models — LLM provider configuration stored in the graph.

The API key is persisted in Neo4j (``:AppSetting {key: 'llm'}``) so the user
can configure their provider from the UI without editing ``.env``; the
response model only ever exposes a masked form of the key. Values stored in
the graph take precedence over the env fallbacks in ``Settings``; the env
values (``LLM_API_KEY`` etc.) remain as a bootstrap/default path.
"""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

# "vllm" and "ollama" are scaffolding only (accepted, validated, stored) —
# both speak the OpenAI-compatible /chat/completions shape today so they
# route through OpenAICompatibleProvider, same as "openai_compatible".
# Dedicated provider classes/defaults land when those integrations are built.
LLM_PROVIDERS = ("gemini", "openai_compatible", "vllm", "ollama")

# Only these URL schemes may reach httpx/the provider client. This blocks the
# classic SSRF-via-scheme-smuggling class (file://, gopher://, ftp://, etc.)
# that a raw string handed to an HTTP client would otherwise allow.
#
# Deliberately NOT resolving DNS or blocking private/loopback IP literals
# here: local vLLM/Ollama endpoints (http://127.0.0.1:.../http://localhost:...)
# are a documented, supported deployment (see docs/GETTING-STARTED.md 7.8).
# Any authenticated user can still redirect the shared provider to an
# external attacker-controlled https:// host — closing that requires
# per-user-scoped or admin-gated settings, which is a separate, larger
# change tracked outside this fix (see 06-SECURITY.md).
_ALLOWED_LLM_URL_SCHEMES = ("http", "https")

# Official Google Gemini REST endpoint (ai.google.dev/gemini-api/docs —
# ``v1beta`` with the ``x-goog-api-key`` header).
DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com"

SETTINGS_KEY_LLM = "llm"


class LLMSettingsUpdate(BaseModel):
    """Body for ``PUT /api/settings/llm``.

    ``api_key`` of ``None``/empty keeps the previously stored key (the GET
    response never returns the full key, so a client that only ever sees the
    masked form can update provider/model without clobbering the secret).
    ``enabled`` of ``None`` keeps the previously stored value.
    """

    model_config = ConfigDict(extra="forbid")

    provider: Literal["gemini", "openai_compatible", "vllm", "ollama"] = "gemini"
    api_key: str | None = Field(default=None, max_length=4096)
    base_url: str | None = Field(default=None, max_length=2048)
    model: str | None = Field(default=None, max_length=256)
    enabled: bool | None = None
    # Which system prompt the GraphRAG agent receives ("Assistant language").
    system_prompt_language: Literal["english", "turkish"] = "english"

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: str | None) -> str | None:
        """Reject non-http(s) schemes and hostless URLs (SSRF-via-scheme guard).

        See the ``_ALLOWED_LLM_URL_SCHEMES`` comment above for what this does
        and deliberately does not cover.
        """
        if value is None or not value.strip():
            return value
        stripped = value.strip()
        parsed = urlparse(stripped)
        if parsed.scheme.lower() not in _ALLOWED_LLM_URL_SCHEMES:
            raise ValueError(
                f"base_url scheme must be one of {_ALLOWED_LLM_URL_SCHEMES}, "
                f"got {parsed.scheme!r}"
            )
        if not parsed.hostname:
            raise ValueError("base_url must include a host")
        return stripped


class LLMSettingsResponse(BaseModel):
    """Effective LLM configuration, with the key masked (T-06-07)."""

    model_config = ConfigDict(extra="forbid")

    provider: Literal["gemini", "openai_compatible", "vllm", "ollama"]
    model: str | None = None
    base_url: str | None = None
    # Effective on/off switch: stored value wins, else the LLM_ENABLED env
    # fallback. When false, every chat/retrieval endpoint returns
    # ``LLM_DISABLED`` (HTTP 503).
    enabled: bool
    # Which system prompt the GraphRAG agent receives.
    system_prompt_language: Literal["english", "turkish"] = "english"
    api_key_configured: bool
    # Never the full key: "••••1234" (last 4 chars) when configured.
    api_key_masked: str | None = None


def mask_api_key(api_key: str | None) -> str | None:
    """Return a display-safe masked form of an API key, or ``None``."""
    if not api_key:
        return None
    if len(api_key) <= 4:
        return "•" * len(api_key)
    return f"••••{api_key[-4:]}"


def settings_payload(
    provider: str,
    api_key: str | None,
    base_url: str | None,
    model: str | None,
    enabled: bool | None = None,
    system_prompt_language: str = "english",
) -> dict[str, Any]:
    """Build the stored JSON payload, dropping empty values."""
    payload: dict[str, Any] = {"provider": provider}
    if api_key:
        payload["api_key"] = api_key
    if base_url:
        payload["base_url"] = base_url
    if model:
        payload["model"] = model
    if enabled is not None:
        payload["enabled"] = enabled
    payload["system_prompt_language"] = system_prompt_language
    return payload
