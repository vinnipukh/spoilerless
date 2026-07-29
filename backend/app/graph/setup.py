from __future__ import annotations

import asyncio

from backend.app.graph.database import Neo4jDatabase
from backend.app.graph.seed import setup_database


async def async_main() -> None:
    database = Neo4jDatabase()
    database.open()
    try:
        await database.verify_connection()
        counts = await setup_database(database)
        print(
            "Dexter graph setup complete: "
            f'{counts["nodes"]} nodes, {counts["relationships"]} relationships'
        )
    finally:
        await database.close()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
