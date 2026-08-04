from __future__ import annotations

from typing import Annotated, Any, Awaitable, Callable, TypeVar

import certifi
from fastapi import Depends, Request
from neo4j import AsyncDriver, AsyncGraphDatabase, TrustCustomCAs

from backend.app.core.config import Settings, get_settings


T = TypeVar("T")
ManagedWork = Callable[[Any, T], Awaitable[Any]]


class Neo4jDatabase:
    """Application-owned async Neo4j driver with no import-time side effects."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._driver: AsyncDriver | None = None

    def open(self) -> None:
        if self._driver is None:
            uri = self._settings.neo4j_uri
            kwargs: dict[str, Any] = {
                "max_connection_pool_size": 50,
                "connection_timeout": 30.0,
                "liveness_check_timeout": 60.0,
            }
            if uri.startswith(("neo4j+s://", "bolt+s://")):
                # Full-TLS schemes (neo4j+s) reject explicit encryption
                # config in driver 6.x (ConfigurationError). Normalize to
                # the plain scheme with explicit encrypted=True plus
                # certifi's trust store so CA verification is deterministic:
                # the Windows OS store on this machine lacks the SSL.com
                # root Aura's chain uses (verified 2026-08-04:
                # SSLCertVerificationError "self-signed certificate in
                # certificate chain"), while certifi verifies the same
                # chain fine (and is complete on Linux/Render).
                uri = uri.replace("neo4j+s://", "neo4j://").replace(
                    "bolt+s://", "bolt://"
                )
                kwargs["encrypted"] = True
                kwargs["trusted_certificates"] = TrustCustomCAs(certifi.where())
            self._driver = AsyncGraphDatabase.driver(
                uri,
                auth=(
                    self._settings.neo4j_username,
                    self._settings.neo4j_password,
                ),
                **kwargs,
            )

    async def verify_connection(self) -> None:
        await self.driver.verify_connectivity()

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None

    @property
    def driver(self) -> AsyncDriver:
        if self._driver is None:
            raise RuntimeError("Neo4j driver has not been initialized")
        return self._driver

    @property
    def database(self) -> str:
        return self._settings.neo4j_database

    async def execute_query(self, query: str, **parameters: Any) -> list[dict[str, Any]]:
        records, _, _ = await self.driver.execute_query(
            query,
            parameters_=parameters,
            database_=self.database,
        )
        return [record.data() for record in records]

    async def execute_write(self, work: ManagedWork, command: T) -> Any:
        """Run one application-owned command in a managed, retryable transaction.

        ``command`` is deliberately created by the caller before this method is
        entered.  Neo4j may invoke ``work`` more than once, so callbacks must be
        pure apart from their transaction writes.
        """
        async with self.driver.session(database=self.database) as session:
            return await session.execute_write(work, command)


def get_database(request: Request) -> Neo4jDatabase:
    return request.app.state.neo4j


def get_driver(database: Annotated[Neo4jDatabase, Depends(get_database)]) -> AsyncDriver:
    return database.driver
