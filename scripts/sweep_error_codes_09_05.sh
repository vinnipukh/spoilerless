#!/usr/bin/env bash
# PROB-09/#20: sweep ALL emitted error codes to the canonical UPPERCASE
# form. Python files: quoted literals only (never bare identifiers like
# test names `..._forbidden`). Docs: word-boundary snake_case tokens
# (they denote codes, not prose).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

declare -A TOKENS=(
  [invalid_request]=INVALID_REQUEST
  [resource_not_found]=RESOURCE_NOT_FOUND
  [series_not_found]=SERIES_NOT_FOUND
  [resource_conflict]=RESOURCE_CONFLICT
  [invalid_visible_until_order]=INVALID_VISIBLE_UNTIL_ORDER
  [invalid_extraction_payload]=INVALID_EXTRACTION_PAYLOAD
  [candidate_not_found]=CANDIDATE_NOT_FOUND
  [cannot_approve_non_candidate]=CANNOT_APPROVE_NON_CANDIDATE
  [too_many_requests]=TOO_MANY_REQUESTS
  [database_unavailable]=DATABASE_UNAVAILABLE
  [database_error]=DATABASE_ERROR
  [constraint_violation]=CONSTRAINT_VIOLATION
  [forbidden]=FORBIDDEN
  [unauthenticated]=UNAUTHENTICATED
  [changeset_stale]=CHANGESET_STALE
  [invalid_action]=INVALID_ACTION
  [cannot_revert_create]=CANNOT_REVERT_CREATE
  [cannot_revert_canonical]=CANNOT_REVERT_CANONICAL
  [resource_already_exists]=RESOURCE_ALREADY_EXISTS
  [ingest_error]=INGEST_ERROR
)

# --- Python: quoted occurrences only ---
PY_FILES=$(git ls-files 'spoilerless/app/*.py' 'spoilerless/tests/*.py')
for token in "${!TOKENS[@]}"; do
  upper=${TOKENS[$token]}
  perl -pi -e "s/\"$token\"/\"$upper\"/g; s/'$token'/'$upper'/g" $PY_FILES
done

# --- Docs: word-boundary snake_case tokens (code references) ---
DOC_FILES="docs/reference/frontend-api-contract.md docs/API.md docs/CONFIGURATION.md docs/architecture/project-spec.md"
for token in "${!TOKENS[@]}"; do
  if [ "$token" = "forbidden" ] || [ "$token" = "unauthenticated" ]; then
    continue  # handled surgically below (prose ambiguity)
  fi
  upper=${TOKENS[$token]}
  perl -pi -e "s/\b$token\b/$upper/g" $DOC_FILES
done

# --- Docs: prose "403 forbidden" / "401 unauthenticated" code references ---
perl -pi -e 's/403 forbidden/403 FORBIDDEN/g; s/401 unauthenticated/401 UNAUTHENTICATED/g; s/`forbidden`/`FORBIDDEN`/g; s/`unauthenticated`/`UNAUTHENTICATED`/g' $DOC_FILES

echo "sweep done"
