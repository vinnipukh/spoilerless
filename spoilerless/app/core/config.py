from functools import lru_cache
import os

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Accept either the aura_* names used in local .env files or the NEO4J_*
    # names used in deployed environments (Render/Aura credential file). The
    # aura_* alias wins when both are present.
    neo4j_uri: str = Field(
        validation_alias=AliasChoices("aura_uri", "neo4j_uri")
    )
    neo4j_username: str = Field(
        validation_alias=AliasChoices("aura_username", "neo4j_username")
    )
    neo4j_password: str = Field(
        validation_alias=AliasChoices("aura_password", "neo4j_password")
    )
    neo4j_database: str = Field(
        default="neo4j",
        validation_alias=AliasChoices("aura_database", "neo4j_database"),
    )

    # Authentication
    google_client_id: str = Field(
        default="",
        description="Google OAuth 2.0 client ID for ID token verification.",
    )
    session_cookie_name: str = Field(
        default="session",
        description="Name of the HttpOnly session cookie.",
    )
    session_ttl_seconds: int = Field(
        default=604800,  # 7 days
        description="Session time-to-live in seconds.",
    )
    session_cookie_samesite: str = Field(
        default="lax",
        description=(
            "SameSite policy for the session cookie. 'lax' (default) is "
            "correct for the same-site custom-domain layout (D-10); choose "
            "'strict' or 'none' (with Secure) deliberately per environment."
        ),
    )
    session_cookie_secure: bool = Field(
        default=True,
        description=(
            "Set the Secure flag on the session cookie. True is the "
            "production-safe default (Render/Vercel are HTTPS-only); local "
            "HTTP dev must explicitly opt out via SESSION_COOKIE_SECURE=false "
            "in .env."
        ),
    )
    frontend_origins: str = Field(
        default="http://localhost:5173",
        description="Comma-separated list of allowed CORS frontend origins.",
    )
    allowed_emails: str = Field(
        default="",
        description=(
            "Comma-separated allowlist of email addresses permitted to sign in. "
            "Empty disables the allowlist (any verified Google account may sign "
            "in) — never leave empty in production."
        ),
    )
    admin_emails: str = Field(
        default="",
        description=(
            "Comma-separated allowlist of email addresses granted the admin "
            "role at login. Empty means no admin exists yet — set this to "
            "grant the first admin."
        ),
    )

    # Rate limiting / cache (Upstash Redis). Empty disables both — see
    # services/rate_limit.py and cache/redis_client.py.
    redis_url: str = Field(
        default="",
        description=(
            "Upstash Redis connection string (rediss://...), used for "
            "rate-limit counters and the graph query response cache. "
            "Empty disables both — see services/rate_limit.py and "
            "cache/redis_client.py."
        ),
    )

    # LLM provider (GraphRAG chat) — backend-only, never exposed to clients.
    llm_enabled: bool = Field(
        default=False,
        description="Enable the LLM-backed GraphRAG chat/retrieval endpoints.",
    )
    llm_provider: str = Field(
        default="openai_compatible",
        description="LLM provider implementation selector.",
    )
    llm_base_url: str = Field(
        default="",
        description="Base URL for the OpenAI-compatible chat completions endpoint.",
    )
    llm_api_key: str = Field(
        default="",
        description="LLM provider API key. Read only inside OpenAICompatibleProvider.",
    )
    llm_model: str = Field(
        default="",
        description="LLM model identifier passed to the provider.",
    )
    llm_timeout_seconds: int = Field(
        default=60,
        description="Per-request timeout for LLM provider calls, in seconds.",
    )
    llm_max_output_tokens: int = Field(
        default=800,
        description="Maximum tokens the model may generate per completion call.",
    )
    llm_temperature: float = Field(
        default=0.0,
        description="Sampling temperature for LLM completions.",
    )
    llm_max_tool_rounds: int = Field(
        default=4,
        description="Maximum bounded tool-calling rounds per chat turn.",
    )
    llm_max_context_items: int = Field(
        default=40,
        description="Maximum number of retrieved context items assembled per turn.",
    )
    llm_max_context_characters: int = Field(
        default=12000,
        description="Maximum total character budget for assembled context per turn.",
    )
    # Optional overrides for the localized insufficient-evidence fallback
    # (see llm/fallbacks.py for the defaults). Empty values fall back to the
    # built-in per-language text.
    llm_fallback_en: str | None = Field(default=None)
    llm_fallback_tr: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def verify_google_client_id_equality(settings: Settings | None = None) -> None:
    """Fail startup when both Google client ids are set but differ (PROB-30/#55).

    The backend verifies ID tokens against ``GOOGLE_CLIENT_ID`` while the
    frontend requests them with ``VITE_GOOGLE_CLIENT_ID`` (root .env via
    vite envDir). A mismatch is the audience-mismatch 503 trigger class
    (#42). The check fires ONLY when both are set — local runs that set
    neither (or only the backend id) must not crash.
    """
    resolved = settings or get_settings()
    backend_id = resolved.google_client_id.strip()
    frontend_id = os.environ.get("VITE_GOOGLE_CLIENT_ID", "").strip()
    if backend_id and frontend_id and backend_id != frontend_id:
        raise RuntimeError(
            "GOOGLE_CLIENT_ID and VITE_GOOGLE_CLIENT_ID mismatch: the backend "
            "verifies Google ID tokens against a different client id than the "
            "frontend requests (audience-mismatch 503 class, #42). Set both "
            "to the same Google OAuth client id in the root .env."
        )