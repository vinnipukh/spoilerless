#!/usr/bin/env bash
# Source this before running tests against the local docker Neo4j:
#   source scripts/env-local.sh && uv run pytest ...
export NEO4J_URI="neo4j://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="hdgraf-local-password"
export NEO4J_DATABASE="neo4j"
