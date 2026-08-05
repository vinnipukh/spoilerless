"""Direct unit tests for the Neo4j database wrapper (PROB-18/#40).

Covers the TLS normalization for Aura schemes (neo4j+s:// → encrypted +
TrustCustomCAs) and the ``$query`` parameter-collision class: a bound
parameter literally named ``query`` collides with the driver method's first
positional argument, so app queries must never use it.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any
from unittest.mock import patch

import pytest

from spoilerless.app.core.config import Settings
from spoilerless.app.graph.database import Neo4jDatabase


def _settings(uri: str) -> Settings:
    return Settings(
        _env_file=None,
        neo4j_uri=uri,
        neo4j_username="u",
        neo4j_password="p",
        neo4j_database="neo4j",
    )


def test_open_normalizes_aura_tls_scheme() -> None:
    db = Neo4jDatabase(_settings("neo4j+s://db.databases.neo4j.io"))
    with patch("spoilerless.app.graph.database.AsyncGraphDatabase.driver") as driver_cls:
        db.open()
    _, kwargs = driver_cls.call_args
    # Scheme normalized to plain neo4j:// with explicit encrypted TLS.
    assert driver_cls.call_args.args[0] == "neo4j://db.databases.neo4j.io"
    assert kwargs["encrypted"] is True
    assert "trusted_certificates" in kwargs  # TrustCustomCAs(certifi) wired
    assert kwargs["auth"] == ("u", "p")


def test_open_plain_bolt_keeps_no_tls_override() -> None:
    db = Neo4jDatabase(_settings("bolt://localhost:7687"))
    with patch("spoilerless.app.graph.database.AsyncGraphDatabase.driver") as driver_cls:
        db.open()
    assert driver_cls.call_args.args[0] == "bolt://localhost:7687"
    assert "encrypted" not in driver_cls.call_args.kwargs


def test_execute_query_forbids_bound_param_named_query() -> None:
    # The driver's first positional arg IS `query`; a bound parameter of the
    # same name collides at the call site (TypeError: multiple values for
    # argument 'query'). The wrapper must never be called with such a param —
    # this regression asserts the failure class so future queries cannot
    # reintroduce it silently.
    db = Neo4jDatabase(_settings("bolt://localhost:7687"))

    class FakeDriver:
        async def execute_query(self, query: str, **kwargs: Any) -> None:
            raise TypeError(
                "execute_query() got multiple values for argument 'query'"
            )

    db._driver = FakeDriver()  # type: ignore[attr-defined]  # inject fake
    with pytest.raises(TypeError, match="multiple values"):
        asyncio.run(db.execute_query("RETURN $query", query="x"))


def test_unopened_driver_raises() -> None:
    db = Neo4jDatabase(_settings("bolt://localhost:7687"))
    with pytest.raises(RuntimeError, match="not been initialized"):
        db.driver  # noqa: B018
