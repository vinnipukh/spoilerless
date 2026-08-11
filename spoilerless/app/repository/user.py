"""Neo4j persistence for application users.

Users are stored as ``(:AppUser {google_sub, email, ...})`` nodes so they can
eventually be related to application content (notes, custom nodes, etc.)
through Neo4j relationships.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from spoilerless.app.graph.database import Neo4jDatabase, neo4j_row_to_python

# Single row-normalization definition (PROB-09/#68) — the byte-identical
# per-repo copies moved to graph/database.neo4j_row_to_python.
_normalize = neo4j_row_to_python


UPSERT_USER_QUERY = """
MERGE (u:AppUser {google_sub: $google_sub})
ON CREATE SET
    u.id = $id,
    u.email = $email,
    u.display_name = $display_name,
    u.avatar_url = $avatar_url,
    u.role = $role,
    u.created_at = $created_at,
    u.updated_at = $updated_at
ON MATCH SET
    u.email = $email,
    u.display_name = $display_name,
    u.avatar_url = $avatar_url,
    u.role = $role,
    u.updated_at = $updated_at
RETURN u.id AS id, u.google_sub AS google_sub,
       u.email AS email, u.display_name AS display_name,
       u.avatar_url AS avatar_url, u.role AS role,
       u.created_at AS created_at, u.updated_at AS updated_at
"""

GET_USER_BY_ID_QUERY = """
MATCH (u:AppUser {id: $id})
RETURN u.id AS id, u.google_sub AS google_sub,
       u.email AS email, u.display_name AS display_name,
       u.avatar_url AS avatar_url,
       coalesce(u.role, 'user') AS role,
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
        role: str,
    ) -> dict[str, Any]:
        """Create a new user or update an existing one by *google_sub*.

        ``role`` is always the caller-supplied value (derived server-side
        from ADMIN_EMAILS at login) — never read from any request body —
        and is re-synced on every login via ``ON MATCH SET u.role = $role``,
        so removing an email from ADMIN_EMAILS demotes the user on their
        next sign-in.

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
            role=role,
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
