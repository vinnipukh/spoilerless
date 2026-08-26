"""Settings domain models — LLM provider configuration stored in the graph.

The API key is persisted in Neo4j (``:AppSetting {key: 'llm'}``) so the user
can configure their provider from the UI without editing ``.env``; the
response model only ever exposes a masked form of the key. Values stored in
the graph take precedence over the env fallbacks in ``Settings``; the env
values (``LLM_API_KEY`` etc.) remain as a bootstrap/default path.
"""

from __future__ import annotations

import concurrent.futures
import ipaddress
import socket
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from spoilerless.app.core.config import get_settings

# "vllm" and "ollama" are scaffolding only (accepted, validated, stored) —
# both speak the OpenAI-compatible /chat/completions shape today so they
# route through OpenAICompatibleProvider, same as "openai_compatible".
# Dedicated provider classes/defaults land when those integrations are built.
LLM_PROVIDERS = ("gemini", "openai_compatible", "vllm", "ollama")

# Only these URL schemes may reach httpx/the provider client. This blocks the
# classic SSRF-via-scheme-smuggling class (file://, gopher://, ftp://, etc.)
# that a raw string handed to an HTTP client would otherwise allow.
_ALLOWED_LLM_URL_SCHEMES = ("http", "https")

# D-06 SSRF hardening: a base_url is rejected when ANY resolved address (v4 or
# v6) falls inside these networks, or when the host is an IP literal in any
# encoding. Enforcement is gated on environment == "production" — local
# vLLM/Ollama loopback usage (docs/GETTING-STARTED.md 7.8) stays usable in
# DEVELOPMENT only; a blocked host is rejected whenever
# get_settings().environment == "production".
_BLOCKED_NETWORKS = tuple(
    ipaddress.ip_network(net)
    for net in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
        "::ffff:0:0/96",
    )
)


def _resolve_host_with_timeout(host: str, timeout_sec: float = 1.0) -> list | None:
    """Resolve ``host`` off-thread, bounded by ``timeout_sec`` (THERMO-P2-02).

    ``socket.getaddrinfo`` is a blocking libc call that can stall for many
    seconds on a dead resolver; run it in a worker thread and give up after
    ``timeout_sec``. The executor is NOT used as a context manager: exiting
    ``with ThreadPoolExecutor(...)`` joins the worker, which would block
    until a hung resolution finishes anyway. ``shutdown(wait=False)`` abandons
    the thread instead, so this helper returns within ~``timeout_sec``.
    """
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(socket.getaddrinfo, host, None)
        return future.result(timeout=timeout_sec)
    except Exception:
        # Unresolvable host (gaierror), timed-out resolution (TimeoutError),
        # or any other failure → caller treats as blocked (fail closed).
        return None
    finally:
        # Abandon rather than join a possibly-hung getaddrinfo worker.
        executor.shutdown(wait=False)


def _host_is_blocked(hostname: str) -> bool:
    """True when the host is loopback/private/link-local/metadata or unresolvable.

    D-06 interpretation: this check is only ENFORCED when
    ``get_settings().environment == "production"`` (see _validate_base_url) —
    local vLLM/Ollama loopback providers stay usable in development.
    Trailing-dot hosts are rejected by the caller BEFORE this helper runs
    (action text is authoritative over the snippet).
    """
    host = hostname.rstrip(".")
    if host.lower() == "localhost":
        return True
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        try:
            addr = ipaddress.ip_address(int(host, 0))
        except (ValueError, OverflowError):
            addr = None
    if addr is not None:
        return any(addr in net for net in _BLOCKED_NETWORKS)

    infos = _resolve_host_with_timeout(host, timeout_sec=1.0)
    if infos is None:
        return True  # unresolvable / timed out → fail closed
    return any(
        ipaddress.ip_address(info[4][0]) in net
        for info in infos
        for net in _BLOCKED_NETWORKS
    )

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
        if parsed.hostname.endswith("."):
            raise ValueError("base_url must not use a trailing-dot host")
        if _host_is_blocked(parsed.hostname) and get_settings().environment == "production":
            raise ValueError(
                "base_url must not point to a loopback, private, link-local, "
                "or metadata address"
            )
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
