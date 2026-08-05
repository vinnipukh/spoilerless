"""Test for the 09-08 startup schema-drift check (PROB-20/#44).

The check (spoilerless/app/graph/setup.py::_check_visibility_schema) verifies
seeded story nodes carry a non-null ``visible_from_order`` — the 01N52 storm
class is a stale DB whose story nodes lost the visibility-gate field. This
test proves it passes on a fresh seed and fires on drift.
"""

from __future__ import annotations

import importlib

import pytest

from spoilerless.app.graph.database import Neo4jDatabase


@pytest.mark.asyncio
async def test_visibility_schema_check_passes_on_fresh_seed() -> None:
    setup = importlib.import_module("spoilerless.app.graph.setup")
    seed = importlib.import_module("spoilerless.app.graph.seed")
    db = Neo4jDatabase()
    db.open()
    try:
        await seed.setup_database(db)
        # Freshly seeded story nodes all carry visible_from_order — no raise.
        await setup._check_visibility_schema(db)  # type: ignore[attr-defined]
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_visibility_schema_check_fires_on_drift() -> None:
    setup = importlib.import_module("spoilerless.app.graph.setup")
    db = Neo4jDatabase()
    db.open()
    try:
        # Simulate drift: remove visible_from_order from one story node (the
        # 01N52 class — a stale DB with a null visibility-gate field).
        await db.execute_query(
            "MATCH (c:Character {id: 'dexter:character:dexter_morgan'}) "
            "REMOVE c.visible_from_order"
        )
        with pytest.raises(RuntimeError, match="SCHEMA DRIFT"):
            await setup._check_visibility_schema(db)  # type: ignore[attr-defined]
    finally:
        # Restore the field so other suites are unaffected.
        await db.execute_query(
            "MATCH (c:Character {id: 'dexter:character:dexter_morgan'}) "
            "SET c.visible_from_order = 1"
        )
        await db.close()
