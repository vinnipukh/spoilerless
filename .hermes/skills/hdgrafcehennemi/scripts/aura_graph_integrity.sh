#!/usr/bin/env bash
# Read-only AuraDB graph integrity audit for hdgrafcehennemi.
# Run after a crash mid-population / sibling agent death to confirm the live
# graph is structurally intact ("is the graph messed up?" check).
# Usage: bash aura_graph_integrity.sh   (from repo root; venv must have neo4j+certifi)
#
# Connection facts (verified 08-04/08-06):
# - Aura creds live in root .env as `aurausername` / `aurapassword` keys.
# - NEO4J_DATABASE = the instance id (e.g. 03a8623b), NEVER 'neo4j'.
# - Use neo4j:// + encrypted=True + TrustCustomCAs(certifi.where()); neo4j+s://
#   with ssl_context= throws ConfigurationError on driver 6.x Windows.
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 1
unset PYTHONPATH
source .venv/Scripts/activate
python - <<'PYEOF'
import os, asyncio
import certifi
from neo4j import AsyncGraphDatabase, TrustCustomCAs

DBID = os.popen("grep '^aurausername' .env | head -1 | cut -d= -f2-").read().strip()
PW = os.popen("grep '^aurapassword' .env | head -1 | cut -d= -f2-").read().strip()
URI = f"neo4j://{DBID}.databases.neo4j.io"

async def main():
    d = AsyncGraphDatabase.driver(URI, auth=(DBID, PW), database=DBID,
                                  encrypted=True,
                                  trusted_certificates=TrustCustomCAs(certifi.where()))
    async with d.session() as s:
        async def q(cy, **p):
            r = await s.run(cy, **p)
            return [x async for x in r]

        print("=== NODE COUNTS BY LABEL ===")
        for row in await q("MATCH (n) RETURN labels(n)[0] AS l, count(*) AS c ORDER BY c DESC"):
            print(f"{row['l']:25s} {row['c']}")

        print("\n=== REL COUNTS BY TYPE ===")
        for row in await q("MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c ORDER BY c DESC"):
            print(f"{row['t']:30s} {row['c']}")

        rows = await q("MATCH (n) RETURN count(n) AS n")
        print(f"\nTOTAL nodes={rows[0]['n']}")
        rows = await q("MATCH ()-[r]->() RETURN count(r) AS n")
        print(f"TOTAL rels={rows[0]['n']}")

        print("\n=== ORPHANED NODES (degree 0) — EXPECTED for seed Characters ===")
        for row in await q("MATCH (n) WHERE NOT (n)--() RETURN labels(n)[0] AS l, n.id AS id LIMIT 30"):
            print(f"{row['l']:20s} id={row['id']}")

        rows = await q("MATCH (n)-[:REFERS_TO]->(t) WHERE t IS NULL RETURN count(n) AS c")
        print(f"\nDANGLING REFERS_TO (missing target): {rows[0]['c']} (must be 0)")

        rows = await q("MATCH (e:Episode) WHERE e.episode_order IS NULL OR e.title IS NULL RETURN count(e) AS c")
        print(f"EPISODES missing core props: {rows[0]['c']} (must be 0)")

        rows = await q("MATCH (c:Claim) WHERE c.series_id IS NULL RETURN count(c) AS c")
        print(f"CLAIMS without series_id: {rows[0]['c']} (must be 0)")

        rows = await q("MATCH (r:Revision) WHERE NOT (r)--() RETURN count(r) AS c")
        print(f"ORPHANED Revisions: {rows[0]['c']} (must be 0)")

        rows = await q("MATCH (n) WHERE n:AppUser OR n:Session RETURN labels(n)[0] AS l, count(*) AS c GROUP BY l")
        print("\nAppUser/Session:", {row['l']: row['c'] for row in rows})
    await d.close()

asyncio.run(main())
PYEOF
