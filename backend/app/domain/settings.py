"""Settings domain models — LLM provider configuration stored in the graph.

The API key is persisted in Neo4j (``:AppSetting {key: 'llm'}``) so the user
can configure their provider from the UI without editing ``.env``; the
response model only ever exposes a masked form of the key. Values stored in
the graph take precedence over the env fallbacks in ``Settings``; the env
values (``LLM_API_KEY`` etc.) remain as a bootstrap/default path.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

LLM_PROVIDERS = ("gemini", "openai_compatible")

# Official Google Gemini REST endpoint (ai.google.dev/gemini-api/docs —
# ``v1beta`` with the ``x-goog-api-key`` header).
DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com"

SETTINGS_KEY_LLM = "llm"


class LLMSettingsUpdate(BaseModel):
    """Body for ``PUT /api/settings/llm``.

    ``api_key`` of ``None``/empty keeps the previously stored key (the GET
    response never returns the full key, so a client that only ever sees the
    masked form can update provider/model without clobbering the secret).
    """

    model_config = ConfigDict(extra="forbid")

    provider: Literal["gemini", "openai_compatible"] = "gemini"
    api_key: str | None = Field(default=None, max_length=4096)
    base_url: str | None = Field(default=None, max_length=2048)
    model: str | None = Field(default=None, max_length=256)


class LLMSettingsResponse(BaseModel):
    """Effective LLM configuration, with the key masked (T-06-07)."""

    model_config = ConfigDict(extra="forbid")

    provider: Literal["gemini", "openai_compatible"]
    model: str | None = None
    base_url: str | None = None
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


def settings_payload(provider: str, api_key: str | None, base_url: str | None, model: str | None) -> dict[str, Any]:
    """Build the stored JSON payload, dropping empty values."""
    payload: dict[str, Any] = {"provider": provider}
    if api_key:
        payload["api_key"] = api_key
    if base_url:
        payload["base_url"] = base_url
    if model:
        payload["model"] = model
    return payload
