from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from spoilerless.app.core.errors import http_error
from spoilerless.app.domain.revision import RevisionAction
from spoilerless.app.domain.user_content import CustomNodeType, NoteTargetType

REVISION_CREATE_QUERY = """
CREATE (revision:Revision {
  id: $id,
  series_id: $series_id,
  resource_type: $resource_type,
  resource_id: $resource_id,
  action: $action,
  before: $before_json,
  after: $after_json,
  visible_from_order: $visible_from_order,
  user_id: $user_id,
  created_at: $created_at
})
RETURN revision.id AS id, revision.series_id AS series_id,
  revision.resource_type AS resource_type, revision.resource_id AS resource_id,
  revision.action AS action, revision.before AS before,
  revision.after AS after, revision.visible_from_order AS visible_from_order,
  revision.user_id AS user_id, revision.created_at AS created_at
"""


_REVERT_LABEL_ALLOWLIST: frozenset[str] = frozenset({
    "Claim",
    "UserNote",
    "ChangeSet",
    "EvidenceFragment",
    *(t.value for t in CustomNodeType),
    *(t.value for t in NoteTargetType),
})


class RevisionRepository:
    """Append-only revision log for user-content mutations.

    Every public method is a static method designed to be called inside
    a managed Neo4j transaction callback (``execute_write``).
    """

    @staticmethod
    def _to_json(value: dict[str, Any] | None) -> str | None:
        """Serialize a dict to JSON string for Neo4j storage."""
        if value is None:
            return None
        # Convert datetime to ISO string for JSON-safe storage
        cleaned = {}
        for k, v in value.items():
            if isinstance(v, datetime):
                cleaned[k] = v.isoformat()
            else:
                cleaned[k] = v
        return json.dumps(cleaned, ensure_ascii=False, default=str)

    @staticmethod
    def _from_json(value: Any) -> dict[str, Any] | None:
        """Deserialize a JSON string back to a dict."""
        if value is None:
            return None
        if isinstance(value, str):
            return json.loads(value)
        # Already a dict (from older/alternative path)
        if isinstance(value, dict):
            return value
        return None

    @staticmethod
    async def log_revision(
        tx: Any,
        *,
        series_id: str,
        resource_type: str,
        resource_id: str,
        action: RevisionAction,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        visible_from_order: int,
        created_at: datetime,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Append one Revision row and return it (including its persisted id).

        ``user_id`` records the acting user (PROB-33, #33) — the id of whoever
        performed the mutation being logged. It is optional only for backward
        safety; every call site in the write path threads the authenticated
        actor. Revisions written before actor attribution carry ``null`` here.
        """
        result = await tx.run(
            REVISION_CREATE_QUERY,
            id=f"revision:{uuid4()}",
            series_id=series_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action.value,
            before_json=RevisionRepository._to_json(before),
            after_json=RevisionRepository._to_json(after),
            visible_from_order=visible_from_order,
            user_id=user_id,
            created_at=created_at,
        )
        record = await result.single()
        assert record is not None, "Revision creation must succeed on existing resource"
        return dict(record.data())

    @staticmethod
    def take_snapshot(row: dict[str, Any]) -> dict[str, Any]:
        """Create a clean, ordered snapshot dict from a Neo4j result row.

        Includes only the fields meaningful for reconstructing what the
        resource looked like at the time of the revision.
        """
        keys = [
            "id",
            "series_id",
            "user_id",
            "type",
            "label",
            "content",
            "target_type",
            "target_id",
            "source",
            "target",
            "predicate",
            "visible_from_order",
            "origin",
            "episode_id",
            "subject_id",
            "object_id",
            "created_at",
            "updated_at",
        ]
        return {k: row[k] for k in keys if k in row and row[k] is not None}


# ── Revert flow (PROB-10/#60) ────────────────────────────────────────────────
# The revert business flow (fetch revision -> action guards -> owner checks ->
# snapshot restore / re-create -> REVERTED log) lives here, NOT in the route.

_IMMUTABLE_FIELDS = frozenset({"id", "series_id", "visible_from_order", "origin"})

REVISION_GET_QUERY = """
MATCH (revision:Revision {id: $revision_id, series_id: $series_id})
WHERE revision.visible_from_order IS NOT NULL
  AND revision.visible_from_order >= 1
  AND revision.visible_from_order <= $visible_until_order
RETURN revision.id AS id, revision.series_id AS series_id,
  revision.resource_type AS resource_type, revision.resource_id AS resource_id,
  revision.action AS action, revision.before AS before,
  revision.after AS after, revision.visible_from_order AS visible_from_order,
  revision.user_id AS user_id, revision.created_at AS created_at
"""


async def revert_revision_work(tx: Any, command: dict[str, Any]) -> dict[str, Any]:
    """Execute a revert inside a single write transaction.

    ``command`` keys: series_id, revision_id, visible_until_order, now,
    user_id, is_admin. Raises the same HTTPExceptions the old route closure
    did (404 RESOURCE_NOT_FOUND, 409 CANNOT_REVERT_CANONICAL /
    RESOURCE_ALREADY_EXISTS, 403 FORBIDDEN, 422 CANNOT_REVERT_CREATE /
    INVALID_ACTION) — envelope behavior is unchanged.
    """
    # 1. Fetch the target revision (must be visible at boundary)
    result = await tx.run(
        REVISION_GET_QUERY,
        revision_id=command["revision_id"],
        series_id=command["series_id"],
        visible_until_order=command["visible_until_order"],
    )
    record = await result.single()
    if record is None:
        raise http_error(404, "RESOURCE_NOT_FOUND", "Resource not found.")
    revision = dict(record.data())

    action = RevisionAction(revision["action"])
    if action == RevisionAction.CREATED:
        raise http_error(
            422,
            "CANNOT_REVERT_CREATE",
            "Cannot revert a Creation revision.",
        )

    resource_id: str = revision["resource_id"]
    resource_type: str = revision["resource_type"]
    # SEC-GR-014: validate labels before interpolation
    if resource_type not in _REVERT_LABEL_ALLOWLIST:
        raise http_error(422, "INVALID_ACTION", "Cannot revert revision with an unknown resource type.")
    # Deserialize the before-snapshot exactly once; target_type lives in it
    # for UserNote — validate if present (SEC-GR-014).
    before_snapshot: dict[str, Any] = RevisionRepository._from_json(revision.get("before")) or {}
    target_type = before_snapshot.get("target_type")
    if target_type is not None and target_type not in _REVERT_LABEL_ALLOWLIST:
        raise http_error(422, "INVALID_ACTION", "Cannot revert revision with an unknown target type.")
    vfo: int = revision["visible_from_order"]

    # 2. Fetch resource (only relevant for UPDATED — DELETED resource is gone)
    if action == RevisionAction.UPDATED:
        result = await tx.run(
            "MATCH (r {id: $rid, series_id: $sid}) RETURN properties(r) AS props",
            rid=resource_id,
            sid=command["series_id"],
        )
        rec = await result.single()
        if rec is None:
            raise http_error(404, "RESOURCE_NOT_FOUND", "Resource not found.")
        resource_props: dict[str, Any] = dict(rec.data()["props"])

        if resource_props.get("origin") != "user":
            raise http_error(
                409,
                "CANNOT_REVERT_CANONICAL",
                "Cannot revert a canonical or candidate resource.",
            )

        # Owner check (PROB-02, #4) — fail closed: unowned/legacy resources
        # (stored_owner is None) require admin (SEC-AUTH-01).
        stored_owner = resource_props.get("user_id")
        if stored_owner != command["user_id"] and not command["is_admin"]:
            raise http_error(
                403,
                "FORBIDDEN",
                "This resource belongs to another user.",
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
            sid=command["series_id"],
            props=restored,
        )

        # Capture new state
        result = await tx.run(
            "MATCH (r {id: $rid, series_id: $sid}) RETURN properties(r) AS props",
            rid=resource_id,
            sid=command["series_id"],
        )
        rec = await result.single()
        new_props = dict(rec.data()["props"]) if rec else {}
        new_snapshot = RevisionRepository.take_snapshot(new_props)

    elif action == RevisionAction.DELETED:
        # Owner check from the stored before-snapshot (the resource is
        # gone, so the snapshot's user_id is the only owner evidence).
        # Revisions logged before owner binding carry no user_id — those
        # are admin-only, fail-closed (SEC-AUTH-01).
        snapshot_owner = before_snapshot.get("user_id")
        if snapshot_owner != command["user_id"] and not command["is_admin"]:
            raise http_error(
                403,
                "FORBIDDEN",
                "This resource belongs to another user.",
            )
        # Check if resource was already re-created (idempotency guard)
        result = await tx.run(
            "MATCH (r {id: $rid, series_id: $sid}) RETURN properties(r) AS props",
            rid=resource_id,
            sid=command["series_id"],
        )
        existing = await result.single()
        if existing is not None:
            raise http_error(
                409,
                "RESOURCE_ALREADY_EXISTS",
                "This resource has already been re-created.",
            )

        old_snapshot = RevisionRepository.take_snapshot(before_snapshot)

        # Set fresh timestamps for the re-created resource
        created_iso = command["now"].isoformat()
        updated_iso = command["now"].isoformat()
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
                nid=resource_id, sid=command["series_id"],
                tid=target_id_val, rid=f"{resource_id}:refers_to", vfo=vfo,
            )

    else:
        raise http_error(
            422,
            "INVALID_ACTION",
            f"Cannot revert revision with action: {action.value}",
        )

    # 3. Log the new REVERTED revision
    revert_record = await RevisionRepository.log_revision(
        tx,
        series_id=command["series_id"],
        resource_type=resource_type,
        resource_id=resource_id,
        action=RevisionAction.REVERTED,
        before=old_snapshot,
        after=new_snapshot,
        visible_from_order=vfo,
        created_at=command["now"],
        user_id=command["user_id"],
    )
    return revert_record
