"""Zombie sweep — dry-run-first cleanup of orphaned :AppUser rows and stale
:Session nodes (PROB-22/#46).

Usage:
    python -m spoilerless.scripts.zombie_sweep --dry-run     # counts only (default)
    python -m spoilerless.scripts.zombie_sweep --execute     # delete after count shown

HARD RULES (enforced in code):
- NEVER delete the protected dev user (see NEVER_DELETE_USER_IDS).
- AppUser rows are deleted ONLY when they have no outgoing/incoming
  ownership edges (no HAS_PROGRESS / HAS_SESSION / CREATED / REFERS_TO ties).
- Sessions are deleted ONLY when expired, revoked, or their owner no longer
  exists.

The script connects with the same TLS normalization as the app
(neo4j+s:// -> neo4j://, encrypted=True, TrustCustomCAs(certifi)) so it can
run against AuraDB from any host. Execution against the live AuraDB is NOT
part of plan 09-08 — that is the checkpoint-gated operator step in plan
09-18. This plan only ships and locally verifies the script.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

# The runbook never-delete list. AuraDB test/dev user — deleting it would
# destroy the operator's live session and graph ownership.
NEVER_DELETE_USER_IDS = frozenset({"ae8a41b7-db96-40e8-b6c2-2e3c69aedb11"})


@dataclass
class SweepCounts:
    zombie_users: int
    stale_sessions: int

    def __add__(self, other: "SweepCounts") -> "SweepCounts":
        return SweepCounts(
            self.zombie_users + other.zombie_users,
            self.stale_sessions + other.stale_sessions,
        )


def _driver():
    from neo4j import GraphDatabase, TrustCustomCAs
    import certifi

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")
    database = os.environ.get("NEO4J_DATABASE", "neo4j")

    # Normalize neo4j+s:// (Aura) the same way graph/database.py does:
    # encrypted TLS with the system CA bundle.
    normalized = uri.replace("neo4j+s://", "neo4j://")
    encrypted = uri.startswith("neo4j+s://")
    config: dict = {"auth": (user, password)}
    if encrypted:
        config["encrypted"] = True
        config["trust"] = TrustCustomCAs(certifi.where())
    driver = GraphDatabase.driver(normalized, **config)
    return driver, database


ZOMBIE_USER_COUNT_QUERY = """
MATCH (u:AppUser)
WHERE NOT u.id IN $protected
  AND NOT EXISTS { (u)-[:HAS_PROGRESS]->(:UserSeriesProgress) }
  AND NOT EXISTS { (u)-[:HAS_SESSION]->(:Session) }
  AND NOT EXISTS { ()-[:CREATED]->(u) }
  AND NOT EXISTS { (u)-[:CREATED]->() }
  AND NOT EXISTS { (u)-[:REFERS_TO]->() }
RETURN count(u) AS n
"""

ZOMBIE_USER_DELETE_QUERY = """
MATCH (u:AppUser)
WHERE NOT u.id IN $protected
  AND NOT EXISTS { (u)-[:HAS_PROGRESS]->(:UserSeriesProgress) }
  AND NOT EXISTS { (u)-[:HAS_SESSION]->(:Session) }
  AND NOT EXISTS { ()-[:CREATED]->(u) }
  AND NOT EXISTS { (u)-[:CREATED]->() }
  AND NOT EXISTS { (u)-[:REFERS_TO]->() }
DETACH DELETE u
RETURN count(u) AS n
"""

STALE_SESSION_COUNT_QUERY = """
MATCH (s:Session)
WHERE s.expires_at < $now
   OR s.revoked_at IS NOT NULL
   OR NOT EXISTS { (s)<-[:HAS_SESSION]-(:AppUser) }
RETURN count(s) AS n
"""

STALE_SESSION_DELETE_QUERY = """
MATCH (s:Session)
WHERE s.expires_at < $now
   OR s.revoked_at IS NOT NULL
   OR NOT EXISTS { (s)<-[:HAS_SESSION]-(:AppUser) }
DETACH DELETE s
RETURN count(s) AS n
"""


def _run_count(driver, database: str, query: str, params: dict) -> int:
    import time

    params = {**params, "now": time.time()}
    with driver.session(database=database) as session:
        record = session.run(query, **params).single()
    return int(record["n"]) if record else 0


def count(driver, database: str) -> SweepCounts:
    return SweepCounts(
        zombie_users=_run_count(driver, database, ZOMBIE_USER_COUNT_QUERY, {"protected": list(NEVER_DELETE_USER_IDS)}),
        stale_sessions=_run_count(driver, database, STALE_SESSION_COUNT_QUERY, {}),
    )


def execute(driver, database: str) -> SweepCounts:
    return SweepCounts(
        zombie_users=_run_count(driver, database, ZOMBIE_USER_DELETE_QUERY, {"protected": list(NEVER_DELETE_USER_IDS)}),
        stale_sessions=_run_count(driver, database, STALE_SESSION_DELETE_QUERY, {}),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print counts only (default behavior; explicit for clarity).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete after printing counts.",
    )
    args = parser.parse_args(argv)

    driver, database = _driver()
    try:
        before = count(driver, database)
        print(f"dry-run counts — zombie AppUser rows: {before.zombie_users}, "
              f"stale Session rows: {before.stale_sessions}")
        if before.zombie_users == 0 and before.stale_sessions == 0:
            print("nothing to sweep; exiting")
            return 0
        if not args.execute:
            print("dry-run only — re-run with --execute to delete")
            return 0

        removed = execute(driver, database)
        after = count(driver, database)
        print(f"removed — zombie AppUser rows: {removed.zombie_users}, "
              f"stale Session rows: {removed.stale_sessions}")
        print(f"remaining — zombie AppUser rows: {after.zombie_users}, "
              f"stale Session rows: {after.stale_sessions}")
        if removed.zombie_users != before.zombie_users or removed.stale_sessions != before.stale_sessions:
            print("WARNING: removed count differs from dry-run count "
                  "(concurrent writes?) — re-run --dry-run to confirm", file=sys.stderr)
            return 2
        return 0
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
