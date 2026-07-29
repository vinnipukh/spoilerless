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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()