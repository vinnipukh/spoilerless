"""Neo4j persistence for application users.

Users are stored as ``(:AppUser {google_sub, email, ...})`` nodes so they can
eventually be related to application content (notes, custom nodes, etc.)
through Neo4j relationships.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from backend.app.graph.database import Neo4jDatabase


def _normalize(record: dict[str, Any]) -> dict[str, Any]:
    """Convert Neo4j-specific types to plain Python/Pydantic-compatible types.

    The Neo4j Python driver returns ``neo4j.time.DateTime`` for nodes
    that were stored with Python ``datetime`` values.  Pydantic's strict
    ``datetime`` validators reject this type, so we normalise to ISO-8601
    strings here at the repository boundary.
    """
    result: dict[str, Any] = {}
    for k, v in record.items():
        if isinstance(v, bytes):
            result[k] = v
        elif hasattr(v, "iso_format"):
            # neo4j.time.DateTime / neo4j.time.Date / neo4j.time.Time
            result[k] = v.iso_format()
        elif hasattr(v, "to_native"):
            # Fallback for other Neo4j temporal types
            native = v.to_native()
            result[k] = native.isoformat() if hasattr(native, "isoformat") else str(native)
        else:
            result[k] = v
    return result


UPSERT_USER_QUERY = """
MERGE (u:AppUser {google_sub: $google_sub})
ON CREATE SET
    u.id = $id,
    u.email = $email,
    u.display_name = $display_name,
    u.avatar_url = $avatar_url,
    u.created_at = $created_at,
    u.updated_at = $updated_at
ON MATCH SET
    u.email = $email,
    u.display_name = $display_name,
    u.avatar_url = $avatar_url,
    u.updated_at = $updated_at
RETURN u.id AS id, u.google_sub AS google_sub,
       u.email AS email, u.display_name AS display_name,
       u.avatar_url AS avatar_url,
       u.created_at AS created_at, u.updated_at AS updated_at
"""

GET_USER_BY_ID_QUERY = """
MATCH (u:AppUser {id: $id})
RETURN u.id AS id, u.google_sub AS google_sub,
       u.email AS email, u.display_name AS display_name,
       u.avatar_url AS avatar_url,
       u.created_at AS created_at, u.updated_at AS updated_at
"""


class UserRepository:
    """Persist and retrieve application users via Neo4j."""

    def __init__(self, database: Neo4jDatabase) -> None:
        self._database = database

    async def upsert(
        self,
        google_sub: str,
        email: str,
        display_name: str,
        avatar_url: str,
    ) -> dict[str, Any]:
        """Create a new user or update an existing one by *google_sub*.

        Returns the full user record as a flat dict.
        """
        now = datetime.now(timezone.utc)
        records = await self._database.execute_query(
            UPSERT_USER_QUERY,
            google_sub=google_sub,
            id=f"user:{uuid4()}",
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            created_at=now,
            updated_at=now,
        )
        return _normalize(records[0])

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Look up a user by application-local ID."""
        records = await self._database.execute_query(
            GET_USER_BY_ID_QUERY, id=user_id
        )
        return _normalize(records[0]) if records else None
