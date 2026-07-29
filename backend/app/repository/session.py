"""Session repository abstraction and in-memory development implementation.

Sessions are opaque token → record maps, not graph data, so they live outside
Neo4j.  Swap ``InMemorySessionRepository`` for a Redis/DB implementation in
production by providing another class that satisfies ``SessionRepository``.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SessionRecord:
    """A single server-side session."""

    hashed_token: str
    user_id: str
    created_at: float  # Unix timestamp
    expires_at: float
    last_seen_at: float
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


class SessionRepository(Protocol):
    """Interface for session persistence.

    Implementations must be safe for concurrent access and should support
    TTL-based expiry cleanup.  The raw (unhashed) token is the public
    identifier returned to clients; only the hashed form is stored server-side.
    """

    async def create(self, user_id: str, ttl_seconds: int) -> str:
        """Create a new session for *user_id*.

        Returns the raw (unhashed) token that should be set as the cookie value.
        The raw token is never stored — only its SHA-256 hash is persisted.
        """
        ...

    async def get(self, raw_token: str) -> SessionRecord | None:
        """Look up a session by its raw (unhashed) token.

        Returns ``None`` when the token is unknown, expired, or revoked.
        """
        ...

    async def refresh(self, raw_token: str, ttl_seconds: int) -> None:
        """Bump *last_seen_at* and extend expiry.  Noop on unknown/revoked."""
        ...

    async def revoke(self, raw_token: str) -> None:
        """Mark the session as revoked.  Noop on unknown tokens."""
        ...


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _generate_token() -> str:
    return secrets.token_urlsafe(48)


class InMemorySessionRepository:
    """Thread-safe in-memory session store for development and testing.

    Sessions are lazily expired on read — no background sweep thread.
    Suitable for single-process dev servers and test suites; **not** suitable
    for multi-process or production deployment.
    """

    def __init__(self) -> None:
        self._store: dict[str, SessionRecord] = {}

    async def create(self, user_id: str, ttl_seconds: int) -> str:
        raw = _generate_token()
        hashed = _hash_token(raw)
        now = time.time()
        record = SessionRecord(
            hashed_token=hashed,
            user_id=user_id,
            created_at=now,
            expires_at=now + ttl_seconds,
            last_seen_at=now,
        )
        self._store[hashed] = record
        return raw

    async def get(self, raw_token: str) -> SessionRecord | None:
        hashed = _hash_token(raw_token)
        record = self._store.get(hashed)
        if record is None:
            return None
        if record.is_expired:
            self._store.pop(hashed, None)
            return None
        if record.is_revoked:
            return None
        return record

    async def refresh(self, raw_token: str, ttl_seconds: int) -> None:
        hashed = _hash_token(raw_token)
        record = self._store.get(hashed)
        if record is None or record.is_expired or record.is_revoked:
            return
        now = time.time()
        self._store[hashed] = SessionRecord(
            hashed_token=hashed,
            user_id=record.user_id,
            created_at=record.created_at,
            expires_at=now + ttl_seconds,
            last_seen_at=now,
        )

    async def revoke(self, raw_token: str) -> None:
        hashed = _hash_token(raw_token)
        record = self._store.get(hashed)
        if record is None:
            return
        self._store[hashed] = SessionRecord(
            hashed_token=hashed,
            user_id=record.user_id,
            created_at=record.created_at,
            expires_at=record.expires_at,
            last_seen_at=record.last_seen_at,
            revoked_at=time.time(),
        )
