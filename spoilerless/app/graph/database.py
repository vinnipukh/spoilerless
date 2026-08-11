from __future__ import annotations

from typing import Any, Awaitable, Callable, TypeVar

import certifi
from fastapi import Request
from neo4j import AsyncDriver, AsyncGraphDatabase, TrustCustomCAs

from spoilerless.app.core.config import Settings, get_settings


T = TypeVar("T")
ManagedWork = Callable[[Any, T], Awaitable[Any]]


def neo4j_row_to_python(record: dict[str, Any]) -> dict[str, Any]:
    """Convert Neo4j temporal types to plain Python/Pydantic-compatible values.

    The driver returns ``neo4j.time.DateTime`` (and friends) for properties
    stored as Python ``datetime``; Pydantic's strict validators reject that
    type, so every repository normalizes to ISO-8601 strings at the boundary.
    One definition instead of the four byte-identical copies (PROB-09/#68).
    """
    result: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, bytes):
            result[key] = value
        elif hasattr(value, "iso_format"):
            result[key] = value.iso_format()
        elif hasattr(value, "to_native"):
            native = value.to_native()
            result[key] = native.isoformat() if hasattr(native, "isoformat") else str(native)
        else:
            result[key] = value
    return result


async def run_single(
    tx: Any,
    query: str,
    error_msg: str,
    *,
    exc_type: type[Exception] = LookupError,
    **params: Any,
) -> dict[str, Any]:
    """Run ``tx.run``, consume one result, raise ``exc_type(error_msg)`` on miss.

    The shared run → single → raise → normalize pattern that used to be
    duplicated as ``_run_create`` (user_content) and ``_run_apply``
    (change_set); each repository aliases it with its own exception type
    (PROB-09/#68).
    """
    record = await (await tx.run(query, **params)).single()
    if record is None:
        raise exc_type(error_msg)
    return neo4j_row_to_python(record.data())


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
