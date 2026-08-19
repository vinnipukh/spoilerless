#!/usr/bin/env bash
# Read-only AuraDB graph integrity audit for hdgrafcehennemi.
# Run after a crash mid-population / sibling agent death to confirm the live
# graph is structurally intact ("is the graph messed up?" check).
# Usage: bash .agents/skills/hdgrafcehennemi/scripts/aura_graph_integrity.sh (from repo root)
#
# Connection facts:
# - Aura creds live in root .env as `aurausername` / `aurapassword` (or NEO4J_USERNAME / NEO4J_PASSWORD).
# - NEO4J_DATABASE = the instance id (e.g. 03a8623b), NEVER 'neo4j'.
# - Use neo4j:// + encrypted=True + TrustCustomCAs(certifi.where()); neo4j+s://
#   with ssl_context= throws ConfigurationError on driver 6.x Windows.
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 1
unset PYTHONPATH

if [ -f ".venv/Scripts/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/Scripts/activate
elif [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

PY_RUNNER="python"
if ! python -c "import neo4j, certifi" >/dev/null 2>&1; then
    if command -v uv >/dev/null 2>&1; then
        PY_RUNNER="uv run python"
    fi
fi

$PY_RUNNER - <<'PYEOF'
import asyncio
import os
import sys
import certifi
from neo4j import AsyncGraphDatabase, TrustCustomCAs

# Parse root .env for credentials
env_vars = {}
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip().strip("'\"")

dbid = env_vars.get("aurausername") or env_vars.get("NEO4J_USERNAME")
pw = env_vars.get("aurapassword") or env_vars.get("NEO4J_PASSWORD")
raw_uri = env_vars.get("NEO4J_URI")

if not dbid or not pw:
    print("Error: AuraDB credentials missing in .env", file=sys.stderr)
    print("Expected 'aurausername'/'aurapassword' or 'NEO4J_USERNAME'/'NEO4J_PASSWORD'.", file=sys.stderr)
    sys.exit(1)

if raw_uri:
    uri = raw_uri.replace("neo4j+s://", "neo4j://")
else:
    uri = f"neo4j://{dbid}.databases.neo4j.io"

async def main():
    d = AsyncGraphDatabase.driver(
        uri,
        auth=(dbid, pw),
        database=dbid,
        encrypted=True,
        trusted_certificates=TrustCustomCAs(certifi.where()),
    )
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

        rows = await q("MATCH ()-[r:REFERS_TO]->(t) WHERE t.id IS NULL RETURN count(r) AS c")
        print(f"\nREFERS_TO targets missing id property: {rows[0]['c']} (must be 0)")

        rows = await q("MATCH (e:Episode) WHERE e.episode_order IS NULL OR e.title IS NULL RETURN count(e) AS c")
        print(f"EPISODES missing core props: {rows[0]['c']} (must be 0)")

        rows = await q("MATCH (c:Claim) WHERE c.series_id IS NULL RETURN count(c) AS c")
        print(f"CLAIMS without series_id: {rows[0]['c']} (must be 0)")

        rows = await q("MATCH (r:Revision) WHERE NOT (r)--() RETURN count(r) AS c")
        print(f"ORPHANED Revisions: {rows[0]['c']} (must be 0)")

        rows = await q("MATCH (n) WHERE n:AppUser OR n:Session RETURN labels(n)[0] AS l, count(*) AS c")
        print("\nAppUser/Session:", {row['l']: row['c'] for row in rows})
    await d.close()

asyncio.run(main())
PYEOF
