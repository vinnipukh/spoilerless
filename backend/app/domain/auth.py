"""Pydantic models for the authentication domain."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GoogleAuthRequest(BaseModel):
    """Request body for POST /api/auth/google."""

    model_config = ConfigDict(extra="forbid")

    credential: str = Field(
        min_length=1,
        description="Google ID token (JWT) returned by the Google Sign-In client.",
    )


class UserPublic(BaseModel):
    """Public user representation returned to the client."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Application-local user identifier.")
    google_sub: str = Field(description="Google's immutable `sub` claim.")
    email: str = Field(description="Verified email from the Google ID token.")
    display_name: str = Field(description="Display name from the Google profile.")
    avatar_url: str = Field(default="", description="Profile image URL.")
    created_at: datetime = Field(description="When the user record was created.")
    updated_at: datetime = Field(description="When the user record was last updated.")


class UserResponse(BaseModel):
    """Top-level response wrapping a user."""

    model_config = ConfigDict(extra="forbid")

    user: UserPublic
