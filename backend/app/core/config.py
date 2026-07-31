from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    neo4j_database: str = "neo4j"

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
    session_cookie_secure: bool = Field(
        default=False,
        description="Set the Secure flag on the session cookie.",
    )
    frontend_origins: str = Field(
        default="http://localhost:5173",
        description="Comma-separated list of allowed CORS frontend origins.",
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()