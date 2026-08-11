from __future__ import annotations

import time
from typing import Protocol
from uuid import uuid4

from spoilerless.app.core.tokens import generate_token, hash_token
from spoilerless.app.domain.share import ShareTokenRecord
from spoilerless.app.graph.database import Neo4jDatabase

# Token hashing/generation live in core/tokens.py (PROB-09/#68); share
# tokens carry 32 bytes of entropy (sessions use the 48-byte default).
_hash_token = hash_token


def _generate_token() -> str:
    return generate_token(32)


class ShareRepository(Protocol):
    """Interface for share token persistence."""

    async def create(
        self,
        created_by: str,
        series_id: str,
        visible_until_order: int,
        ttl_seconds: int = 2592000,
    ) -> tuple[str, ShareTokenRecord]:
        """Create a new share token.

        Returns (raw_token, record). Only the token_hash is stored.
        """
        ...

    async def get_by_token_hash(self, token_hash: str) -> ShareTokenRecord | None:
        """Look up active share token by token_hash."""
        ...

    async def get_by_raw_token(self, raw_token: str) -> ShareTokenRecord | None:
        """Look up active share token by raw token."""
        ...

    async def revoke(self, token_hash: str) -> bool:
        """Revoke a token by token_hash."""
        ...

    async def revoke_by_raw_token(self, raw_token: str) -> bool:
        """Revoke a token by raw token."""
        ...

    async def list_active(self, created_by: str) -> list[ShareTokenRecord]:
        """List active tokens created by user_id."""
        ...

    async def sweep_expired(self) -> int:
        """Sweep expired or revoked tokens."""
        ...


class InMemoryShareRepository:
    """Thread-safe in-memory share token store for testing and dev."""

    def __init__(self) -> None:
        self._store: dict[str, ShareTokenRecord] = {}

    async def create(
        self,
        created_by: str,
        series_id: str,
        visible_until_order: int,
        ttl_seconds: int = 2592000,
    ) -> tuple[str, ShareTokenRecord]:
        raw = _generate_token()
        hashed = _hash_token(raw)
        now = time.time()
        record = ShareTokenRecord(
            id=f"sharetoken:{uuid4()}",
            token_hash=hashed,
            series_id=series_id,
            visible_until_order=visible_until_order,
            created_at=now,
            expires_at=now + ttl_seconds,
            created_by=created_by,
            revoked_at=None,
        )
        self._store[hashed] = record
        return raw, record

    async def get_by_token_hash(self, token_hash: str) -> ShareTokenRecord | None:
        record = self._store.get(token_hash)
        if record is None:
            return None
        if record.is_expired or record.is_revoked:
            return None
        return record

    async def get_by_raw_token(self, raw_token: str) -> ShareTokenRecord | None:
        return await self.get_by_token_hash(_hash_token(raw_token))

    async def revoke(self, token_hash: str) -> bool:
        record = self._store.get(token_hash)
        if record is None or record.is_revoked:
            return False
        self._store[token_hash] = ShareTokenRecord(
            id=record.id,
            token_hash=record.token_hash,
            series_id=record.series_id,
            visible_until_order=record.visible_until_order,
            created_at=record.created_at,
            expires_at=record.expires_at,
            created_by=record.created_by,
            revoked_at=time.time(),
        )
        return True

    async def revoke_by_raw_token(self, raw_token: str) -> bool:
        return await self.revoke(_hash_token(raw_token))

    async def list_active(self, created_by: str) -> list[ShareTokenRecord]:
        return [
            rec
            for rec in self._store.values()
            if rec.created_by == created_by and rec.is_valid
        ]

    async def sweep_expired(self) -> int:
        to_delete = [
            h for h, rec in self._store.items() if rec.is_expired or rec.is_revoked
        ]
        for h in to_delete:
            del self._store[h]
        return len(to_delete)


class Neo4jShareRepository:
    """Neo4j persistent store for share tokens on (:ShareToken) label."""

    LABEL = "ShareToken"

    def __init__(self, database: Neo4jDatabase) -> None:
        self._database = database

    async def create(
        self,
        created_by: str,
        series_id: str,
        visible_until_order: int,
        ttl_seconds: int = 2592000,
    ) -> tuple[str, ShareTokenRecord]:
        raw = _generate_token()
        hashed = _hash_token(raw)
        now = time.time()
        record_id = f"sharetoken:{uuid4()}"
        expires_at = now + ttl_seconds

        await self._database.execute_query(
            f"""\
            CREATE (s:{self.LABEL} {{
                id: $id,
                token_hash: $token_hash,
                series_id: $series_id,
                visible_until_order: $visible_until_order,
                created_at: $now,
                expires_at: $expires_at,
                created_by: $created_by,
                revoked_at: NULL
            }})
            WITH s
            OPTIONAL MATCH (u:AppUser {{id: $created_by}})
            FOREACH (_ IN CASE WHEN u IS NOT NULL THEN [1] ELSE [] END |
                CREATE (u)-[:CREATED_SHARE]->(s)
            )
            """,
            id=record_id,
            token_hash=hashed,
            series_id=series_id,
            visible_until_order=visible_until_order,
            now=now,
            expires_at=expires_at,
            created_by=created_by,
        )
        record = ShareTokenRecord(
            id=record_id,
            token_hash=hashed,
            series_id=series_id,
            visible_until_order=visible_until_order,
            created_at=now,
            expires_at=expires_at,
            created_by=created_by,
            revoked_at=None,
        )
        return raw, record

    async def get_by_token_hash(self, token_hash: str) -> ShareTokenRecord | None:
        now = time.time()
        records = await self._database.execute_query(
            f"""\
            MATCH (s:{self.LABEL} {{token_hash: $token_hash}})
            WHERE s.revoked_at IS NULL
              AND s.expires_at > $now
            RETURN s.id AS id,
                   s.token_hash AS token_hash,
                   s.series_id AS series_id,
                   s.visible_until_order AS visible_until_order,
                   s.created_at AS created_at,
                   s.expires_at AS expires_at,
                   s.created_by AS created_by,
                   s.revoked_at AS revoked_at
            """,
            token_hash=token_hash,
            now=now,
        )
        if not records:
            return None
        rec = records[0]
        return ShareTokenRecord(
            id=rec["id"],
            token_hash=rec["token_hash"],
            series_id=rec["series_id"],
            visible_until_order=rec["visible_until_order"],
            created_at=rec["created_at"],
            expires_at=rec["expires_at"],
            created_by=rec["created_by"],
            revoked_at=rec.get("revoked_at"),
        )

    async def get_by_raw_token(self, raw_token: str) -> ShareTokenRecord | None:
        return await self.get_by_token_hash(_hash_token(raw_token))

    async def revoke(self, token_hash: str) -> bool:
        now = time.time()
        records = await self._database.execute_query(
            f"""\
            MATCH (s:{self.LABEL} {{token_hash: $token_hash}})
            WHERE s.revoked_at IS NULL
            SET s.revoked_at = $now
            RETURN s.id AS id
            """,
            token_hash=token_hash,
            now=now,
        )
        return len(records) > 0

    async def revoke_by_raw_token(self, raw_token: str) -> bool:
        return await self.revoke(_hash_token(raw_token))

    async def list_active(self, created_by: str) -> list[ShareTokenRecord]:
        now = time.time()
        records = await self._database.execute_query(
            f"""\
            MATCH (s:{self.LABEL} {{created_by: $created_by}})
            WHERE s.revoked_at IS NULL
              AND s.expires_at > $now
            RETURN s.id AS id,
                   s.token_hash AS token_hash,
                   s.series_id AS series_id,
                   s.visible_until_order AS visible_until_order,
                   s.created_at AS created_at,
                   s.expires_at AS expires_at,
                   s.created_by AS created_by,
                   s.revoked_at AS revoked_at
            ORDER BY s.created_at DESC
            """,
            created_by=created_by,
            now=now,
        )
        return [
            ShareTokenRecord(
                id=rec["id"],
                token_hash=rec["token_hash"],
                series_id=rec["series_id"],
                visible_until_order=rec["visible_until_order"],
                created_at=rec["created_at"],
                expires_at=rec["expires_at"],
                created_by=rec["created_by"],
                revoked_at=rec.get("revoked_at"),
            )
            for rec in records
        ]

    async def sweep_expired(self) -> int:
        now = time.time()
        records = await self._database.execute_query(
            f"""\
            MATCH (s:{self.LABEL})
            WHERE s.expires_at <= $now OR s.revoked_at IS NOT NULL
            DETACH DELETE s
            RETURN count(s) AS count
            """,
            now=now,
        )
        if not records:
            return 0
        return int(records[0]["count"])
