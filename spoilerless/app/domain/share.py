from __future__ import annotations

import time
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ShareTokenCreate(BaseModel):
    """Internal model for share token creation request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    series_id: Annotated[str, Field(min_length=1, max_length=255)]
    visible_until_order: Annotated[int, Field(gt=0)]


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
