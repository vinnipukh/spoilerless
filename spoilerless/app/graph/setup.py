from __future__ import annotations

import asyncio
import sys

from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.graph.labels import STORY_LABELS
from spoilerless.app.graph.seed import setup_database


# PROB-20/#44 startup schema check: a stale live DB whose seeded story nodes
# lost their visibility-gate fields is exactly the 01N52 storm class. After
# seeding, verify every seeded story node carries a non-null
# ``visible_from_order`` so drift cannot hide again. Null values are the
# failure — the seed never ships a null visibility order for a story node.
# The story-label inventory lives in graph/labels.py (PROB-09/#81).


async def _check_visibility_schema(database: Neo4jDatabase) -> None:
    rows = await database.execute_query(
        """
        MATCH (node) WHERE node.series_id = $series_id
          AND any(label IN labels(node) WHERE label IN $labels)
        WITH collect(node) AS nodes
        RETURN size(nodes) AS total,
               size([n IN nodes WHERE n.visible_from_order IS NULL]) AS missing
        """,
        series_id="series_dexter",
        labels=list(STORY_LABELS),
    )
    if not rows:
        return
    row = rows[0]
    total = int(row["total"])
    missing = int(row["missing"])
    if total == 0:
        return
    if missing > 0:
        raise RuntimeError(
            "SCHEMA DRIFT: seeded story nodes are missing the visibility-gate "
            f"field visible_from_order ({missing}/{total} null). A stale live "
            "DB cannot hide again — re-run setup against the target DB "
            "(plan 09-18 operator step)."
        )


async def async_main() -> None:
    database = Neo4jDatabase()
    database.open()
    try:
        await database.verify_connection()
        counts = await setup_database(database)
        await _check_visibility_schema(database)
        print(
            "Dexter graph setup complete: "
            f'{counts["nodes"]} nodes, {counts["relationships"]} relationships'
        )
    finally:
        await database.close()


def main() -> None:
    try:
        asyncio.run(async_main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
