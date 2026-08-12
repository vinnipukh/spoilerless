from __future__ import annotations

import time
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ShareCreateRequest(BaseModel):
    """Create-a-snapshot-link request body (was defined in api/share.py —
    PROB-09 #81 moves router request/response models into the domain)."""

    model_config = ConfigDict(extra="forbid")

    series_id: Annotated[str, Field(min_length=1, max_length=255)]
    visible_until_order: Annotated[int, Field(gt=0)]


class ShareCreateResponse(BaseModel):
    """Create-a-snapshot-link response (the raw token is shown exactly once)."""

    model_config = ConfigDict(extra="forbid")

    token: str
    expires_at: float
    url: str
    series_id: str
    visible_until_order: int
    created_at: float


class ShareItemResponse(BaseModel):
    """List-active-tokens row."""

    model_config = ConfigDict(extra="forbid")

    id: str
    token_hash: str
    series_id: str
    visible_until_order: int
    created_at: float
    expires_at: float


class ShareTokenRecord(BaseModel):
    """Server-side record of a shareable snapshot token."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    token_hash: str
    series_id: str
    visible_until_order: int
    created_at: float
    expires_at: float
    created_by: str
    revoked_at: float | None = None

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_valid(self) -> bool:
        return not self.is_expired and not self.is_revoked
