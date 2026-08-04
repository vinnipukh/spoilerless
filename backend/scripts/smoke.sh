#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:5173}"
NEO4J_BROWSER_URL="${NEO4J_BROWSER_URL:-http://127.0.0.1:7474}"
PASS_COUNT=0
# Keep temp files on a Windows-native project-relative path so both Git Bash tools
# and the Windows Python launched by uv can read them without MSYS path translation.
TMP_DIR="$(mktemp -d .smoke-tmp.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  printf 'PASS %02d: %s\n' "$PASS_COUNT" "$1"
}

curl -fsS "$NEO4J_BROWSER_URL" > "$TMP_DIR/neo4j.html"
pass "Neo4j Browser reachable"

curl -fsS "$BACKEND_URL/docs" > "$TMP_DIR/docs.html"
pass "FastAPI Swagger reachable"

curl -fsS "$FRONTEND_URL" > "$TMP_DIR/frontend.html"
pass "React development server reachable"

uv run python -m spoilerless.app.graph.setup > "$TMP_DIR/setup.txt"
grep -q "Dexter graph setup complete: 41 nodes, 26 relationships" "$TMP_DIR/setup.txt"
pass "deterministic setup completed"

curl -fsS "$BACKEND_URL/health" > "$TMP_DIR/health.json"
uv run python - "$TMP_DIR/health.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    payload = json.load(stream)
assert payload == {
    "status": "ok",
    "database": "connected",
    "service": "spoilerless-backend",
}
PY
pass "database-backed health is connected"

curl -fsS "$BACKEND_URL/api/series" > "$TMP_DIR/series.json"
curl -fsS "$BACKEND_URL/api/series/series_dexter/episodes" > "$TMP_DIR/episodes.json"
uv run python - "$TMP_DIR/series.json" "$TMP_DIR/episodes.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    series = json.load(stream)
with open(sys.argv[2], encoding="utf-8") as stream:
    episodes = json.load(stream)
assert series == [{"id": "series_dexter", "title": "Dexter", "slug": "dexter"}]
assert [episode["episode_order"] for episode in episodes] == [1, 2, 3]
PY
pass "series and ordered episode metadata APIs"

curl -fsS "$BACKEND_URL/api/series/series_dexter/graph?visible_until_order=1" > "$TMP_DIR/graph.json"
uv run python - "$TMP_DIR/graph.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    payload = json.load(stream)
serialized = json.dumps(payload).lower()
assert payload["visible_until_order"] == 1
assert len(payload["nodes"]) == 11
assert "dexter_s01e02" not in serialized
assert "dexter_s01e03" not in serialized
node_ids = {node["id"] for node in payload["nodes"]}
assert all(edge["source"] in node_ids and edge["target"] in node_ids for edge in payload["edges"])
PY
pass "order-1 graph excludes future sentinels and is closed"

response="$(curl -sS -w $'\n%{http_code}' \
  "$BACKEND_URL/api/series/series_dexter/graph?visible_until_order=4")"
status="${response##*$'\n'}"
printf '%s' "${response%$'\n'*}" > "$TMP_DIR/invalid.json"
test "$status" = "422"
uv run python - "$TMP_DIR/invalid.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    payload = json.load(stream)
assert payload["detail"]["code"] == "invalid_visible_until_order"
PY
pass "invalid non-persisted boundary returns stable 422"

printf 'SMOKE PASS: %d/8 checks passed\n' "$PASS_COUNT"
