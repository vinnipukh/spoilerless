from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from backend.app.core.errors import error_responses, http_error
from backend.app.domain.revision import RevisionAction, RevisionResponse
from backend.app.graph.database import Neo4jDatabase, get_database
from backend.app.revisions import RevisionRepository

router = APIRouter(prefix="/api/series", tags=["revisions"])
DatabaseDependency = Annotated[Neo4jDatabase, Depends(get_database)]
Boundary = Annotated[
    int, Query(gt=0, description="Persisted positive spoiler boundary.", examples=[1])
]

_IMMUTABLE_FIELDS = frozenset({"id", "series_id", "visible_from_order", "origin"})

REVISION_LIST_QUERY = """
MATCH (revision:Revision {series_id: $series_id})
WHERE revision.visible_from_order IS NOT NULL
  AND revision.visible_from_order >= 1
  AND revision.visible_from_order <= $visible_until_order
  AND ($resource_type IS NULL OR revision.resource_type = $resource_type)
  AND ($resource_id IS NULL OR revision.resource_id = $resource_id)
RETURN revision.id AS id, revision.series_id AS series_id,
  revision.resource_type AS resource_type, revision.resource_id AS resource_id,
  revision.action AS action, revision.before AS before,
  revision.after AS after, revision.visible_from_order AS visible_from_order,
  revision.created_at AS created_at
ORDER BY revision.created_at DESC, revision.id ASC
"""

REVISION_GET_QUERY = """
MATCH (revision:Revision {id: $revision_id, series_id: $series_id})
WHERE revision.visible_from_order IS NOT NULL
  AND revision.visible_from_order >= 1
  AND revision.visible_from_order <= $visible_until_order
RETURN revision.id AS id, revision.series_id AS series_id,
  revision.resource_type AS resource_type, revision.resource_id AS resource_id,
  revision.action AS action, revision.before AS before,
  revision.after AS after, revision.visible_from_order AS visible_from_order,
  revision.created_at AS created_at
"""


def _not_found() -> Exception:
    return http_error(404, "resource_not_found", "Resource not found.")


# ---------------------------------------------------------------------------
# GET /api/series/{series_id}/revisions
# ---------------------------------------------------------------------------


@router.get(
    "/{series_id}/revisions",
    response_model=list[RevisionResponse],
    summary="List visible revisions for a series",
    responses=error_responses(422, 503),
)
async def list_revisions(
    series_id: str,
    visible_until_order: Boundary,
    database: DatabaseDependency,
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
) -> list[RevisionResponse]:
    if resource_type is not None and resource_type.strip() == "":
        resource_type = None
    if resource_id is not None and resource_id.strip() == "":
        resource_id = None

    rows = await database.execute_query(
        REVISION_LIST_QUERY,
        series_id=series_id,
        visible_until_order=visible_until_order,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    return [RevisionResponse.model_validate(row) for row in rows]


# ---------------------------------------------------------------------------
# GET /api/series/{series_id}/revisions/{revision_id}
# ---------------------------------------------------------------------------


@router.get(
    "/{series_id}/revisions/{revision_id}",
    response_model=RevisionResponse,
    summary="Get a single revision by ID",
    responses=error_responses(404, 422, 503),
)
async def get_revision(
    series_id: str,
    revision_id: str,
    visible_until_order: Boundary,
    database: DatabaseDependency,
) -> RevisionResponse:
    rows = await database.execute_query(
        REVISION_GET_QUERY,
        revision_id=revision_id,
        series_id=series_id,
        visible_until_order=visible_until_order,
    )
    if not rows:
        raise _not_found()
    return RevisionResponse.model_validate(rows[0])


# ---------------------------------------------------------------------------
# POST /api/series/{series_id}/revisions/{revision_id}/revert
# ---------------------------------------------------------------------------


@router.post(
    "/{series_id}/revisions/{revision_id}/revert",
    response_model=RevisionResponse,
    summary="Revert a resource to the state captured in a revision",
    responses=error_responses(404, 409, 422, 503),
)
async def revert_revision(
    series_id: str,
    revision_id: str,
    visible_until_order: Boundary,
    database: DatabaseDependency,
) -> RevisionResponse:
    now = datetime.now(timezone.utc)

    async def _revert_work(tx: Any, _cmd: dict[str, Any]) -> dict[str, Any]:
        """Execute revert inside a single write transaction."""

        # 1. Fetch the target revision (must be visible at boundary)
        result = await tx.run(
            REVISION_GET_QUERY,
            revision_id=_cmd["revision_id"],
            series_id=_cmd["series_id"],
            visible_until_order=_cmd["visible_until_order"],
        )
        record = await result.single()
        if record is None:
            raise _not_found()
        revision = dict(record.data())

        action = RevisionAction(revision["action"])
        if action == RevisionAction.CREATED:
            raise http_error(
                422,
                "cannot_revert_create",
                "Cannot revert a Creation revision.",
            )

        resource_id: str = revision["resource_id"]
        resource_type: str = revision["resource_type"]
        before_snapshot_raw: dict[str, Any] | None = RevisionRepository._from_json(revision.get("before"))
        before_snapshot: dict[str, Any] = before_snapshot_raw or {}
        vfo: int = revision["visible_from_order"]

        # 2. Fetch resource (only relevant for UPDATED — DELETED resource is gone)
        if action == RevisionAction.UPDATED:
            result = await tx.run(
                "MATCH (r {id: $rid, series_id: $sid}) RETURN properties(r) AS props",
                rid=resource_id,
                sid=_cmd["series_id"],
            )
            rec = await result.single()
            if rec is None:
                raise _not_found()
            resource_props: dict[str, Any] = dict(rec.data()["props"])

            if resource_props.get("origin") != "user":
                raise http_error(
                    409,
                    "cannot_revert_canonical",
                    "Cannot revert a canonical or candidate resource.",
                )

            old_snapshot = RevisionRepository.take_snapshot(resource_props)

            # Restore mutable fields from before snapshot
            restored = {
                k: v
                for k, v in before_snapshot.items()
                if k not in _IMMUTABLE_FIELDS
            }
            await tx.run(
                "MATCH (r {id: $rid, series_id: $sid}) SET r += $props",
                rid=resource_id,
                sid=_cmd["series_id"],
                props=restored,
            )

            # Capture new state
            result = await tx.run(
                "MATCH (r {id: $rid, series_id: $sid}) RETURN properties(r) AS props",
                rid=resource_id,
                sid=_cmd["series_id"],
            )
            rec = await result.single()
            new_props = dict(rec.data()["props"]) if rec else {}
            new_snapshot = RevisionRepository.take_snapshot(new_props)

        elif action == RevisionAction.DELETED:
            # Check if resource was already re-created (idempotency guard)
            result = await tx.run(
                "MATCH (r {id: $rid, series_id: $sid}) RETURN properties(r) AS props",
                rid=resource_id,
                sid=_cmd["series_id"],
            )
            existing = await result.single()
            if existing is not None:
                raise http_error(
                    409,
                    "resource_already_exists",
                    "This resource has already been re-created.",
                )

            old_snapshot = RevisionRepository.take_snapshot(before_snapshot)

            # Set fresh timestamps for the re-created resource
            created_iso = _cmd["now"].isoformat()
            updated_iso = _cmd["now"].isoformat()
            fresh_props = dict(before_snapshot)
            fresh_props["created_at"] = created_iso
            fresh_props["updated_at"] = updated_iso

            # Re-create the resource node with the stored before snapshot
            create_query = (
                f"CREATE (r:{resource_type} $props) RETURN properties(r) AS props"
            )
            result = await tx.run(create_query, props=fresh_props)
            rec = await result.single()
            new_props = dict(rec.data()["props"]) if rec else before_snapshot
            new_snapshot = RevisionRepository.take_snapshot(new_props)

            # Restore REFERS_TO relationship for UserNote (required by GET query)
            if resource_type == "UserNote" and "target_id" in before_snapshot and "target_type" in before_snapshot:
                target_type = before_snapshot.get("target_type", "Character")
                target_id_val = before_snapshot["target_id"]
                await tx.run(
                    "MATCH (note:UserNote {id: $nid, series_id: $sid}) "
                    f"MATCH (target:{target_type} {{id: $tid, series_id: $sid}}) "
                    "CREATE (note)-[:REFERS_TO {id: $rid, series_id: $sid, "
                    "visible_from_order: $vfo, origin: 'user'}]->(target)",
                    nid=resource_id, sid=_cmd["series_id"],
                    tid=target_id_val, rid=f"{resource_id}:refers_to", vfo=vfo,
                )

        else:
            raise http_error(
                422,
                "invalid_action",
                f"Cannot revert revision with action: {action.value}",
            )

        # 3. Log the new REVERTED revision
        revert_record = await RevisionRepository.log_revision(
            tx,
            series_id=_cmd["series_id"],
            resource_type=resource_type,
            resource_id=resource_id,
            action=RevisionAction.REVERTED,
            before=old_snapshot,
            after=new_snapshot,
            visible_from_order=vfo,
            created_at=_cmd["now"],
        )
        return revert_record

    command = {
        "series_id": series_id,
        "revision_id": revision_id,
        "visible_until_order": visible_until_order,
        "now": now,
    }
    result = await database.execute_write(_revert_work, command)
    return RevisionResponse.model_validate(result)
