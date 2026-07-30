"""Session repository abstraction, in-memory dev implementation, and Neo4j
persistent implementation.

Session cleanup strategy
------------------------
Expired and revoked ``Session`` nodes accumulate in the database.  A periodic
background task (e.g. a cron job or FastAPI lifespan background task) should
run::

    MATCH (s:Session)
    WHERE s.expires_at < timestamp() OR s.revoked_at IS NOT NULL
    DETACH DELETE s

This is not implemented in this task — the app relies on lazy rejection of
expired/revoked sessions at read time.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

from backend.app.graph.database import Neo4jDatabase


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


# ===================================================================
# In-memory implementation (development / testing)
# ===================================================================


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


# ===================================================================
# Neo4j-persistent implementation
# ===================================================================


class Neo4jSessionRepository:
    """Server-side sessions persisted as ``(:Session)`` nodes in Neo4j.

    Each session node stores a SHA-256 hash of the opaque token (never the
    raw token), along with expiry and revocation timestamps.  A
    ``(:AppUser)-[:HAS_SESSION]->(:Session)`` relationship links the session
    to its owning user.

    Required constraints (added in :py:mod:`backend.app.graph.seed`)::

      CREATE CONSTRAINT IF NOT EXISTS FOR (s:Session) REQUIRE s.id IS UNIQUE
      CREATE CONSTRAINT IF NOT EXISTS FOR (s:Session) REQUIRE s.token_hash IS UNIQUE
      CREATE INDEX IF NOT EXISTS FOR (s:Session) ON (s.expires_at)
    """

    # Session labelled ``Session`` — same as the domain concept, no prefix.
    LABEL = "Session"

    def __init__(self, database: Neo4jDatabase) -> None:
        self._database = database

    async def create(self, user_id: str, ttl_seconds: int) -> str:
        raw = _generate_token()
        hashed = _hash_token(raw)
        now = time.time()
        await self._database.execute_query(
            f"""\
            CREATE (s:{self.LABEL} {{
                id: $id,
                token_hash: $token_hash,
                created_at: $now,
                expires_at: $now + $ttl,
                last_seen_at: $now,
                revoked_at: NULL
            }})
            WITH s
            MATCH (u:AppUser {{id: $user_id}})
            CREATE (u)-[:HAS_SESSION]->(s)
            """,
            id=f"session:{user_id}:{int(now)}",
            token_hash=hashed,
            user_id=user_id,
            now=now,
            ttl=float(ttl_seconds),
        )
        return raw

    async def get(self, raw_token: str) -> SessionRecord | None:
        hashed = _hash_token(raw_token)
        now = time.time()
        records = await self._database.execute_query(
            f"""\
            MATCH (s:{self.LABEL} {{token_hash: $token_hash}})
            WHERE s.revoked_at IS NULL
              AND s.expires_at > $now
            RETURN s.token_hash AS token_hash,
                   s.id AS session_id,
                   [(s)-[:HAS_SESSION]->(u:AppUser) | u.id][0] AS user_id,
                   s.created_at AS created_at,
                   s.expires_at AS expires_at,
                   s.last_seen_at AS last_seen_at,
                   s.revoked_at AS revoked_at
            """,
            token_hash=hashed,
            now=now,
        )
        if not records:
            return None
        rec = records[0]
        return SessionRecord(
            hashed_token=rec["token_hash"],
            user_id=rec["user_id"],
            created_at=rec["created_at"],
            expires_at=rec["expires_at"],
            last_seen_at=rec["last_seen_at"],
            revoked_at=rec.get("revoked_at"),
        )

    async def refresh(self, raw_token: str, ttl_seconds: int) -> None:
        hashed = _hash_token(raw_token)
        now = time.time()
        await self._database.execute_query(
            f"""\
            MATCH (s:{self.LABEL} {{token_hash: $token_hash}})
            WHERE s.revoked_at IS NULL
            SET s.last_seen_at = $now,
                s.expires_at = $now + $ttl
            """,
            token_hash=hashed,
            now=now,
            ttl=float(ttl_seconds),
        )

    async def revoke(self, raw_token: str) -> None:
        hashed = _hash_token(raw_token)
        await self._database.execute_query(
            f"""\
            MATCH (s:{self.LABEL} {{token_hash: $token_hash}})
            SET s.revoked_at = timestamp()
            """,
            token_hash=hashed,
        )
