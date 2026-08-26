from __future__ import annotations

from typing import Any

from spoilerless.app.domain.revision import RevisionAction
from spoilerless.app.domain.user_content import CustomNodeType, NoteTargetType
from spoilerless.app.revisions.repository import REVISION_GET_QUERY, RevisionRepository


class RevisionError(Exception):
    """Base domain exception for revision operations."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message or super().__str__()


class RevisionNotFound(RevisionError):
    """Raised when the requested revision or resource is not found."""


class RevisionForbidden(RevisionError):
    """Raised when the acting user lacks permission for the revision operation."""


class RevisionCannotRevertCreate(RevisionError):
    """Raised when attempting to revert a Creation revision."""


class RevisionCannotRevertCanonical(RevisionError):
    """Raised when attempting to revert a canonical or candidate resource."""


class RevisionAlreadyExists(RevisionError):
    """Raised when attempting to re-create an already existing resource."""


class RevisionInvalidAction(RevisionError):
    """Raised when an invalid action or resource type is encountered."""


_REVERT_LABEL_ALLOWLIST: frozenset[str] = frozenset({
    "Claim",
    "UserNote",
    "ChangeSet",
    "EvidenceFragment",
    *(t.value for t in CustomNodeType),
    *(t.value for t in NoteTargetType),
})

_IMMUTABLE_FIELDS = frozenset({"id", "series_id", "visible_from_order", "origin"})


async def revert_revision_work(tx: Any, command: dict[str, Any]) -> dict[str, Any]:
    """Execute a revert inside a single write transaction.

    ``command`` keys: series_id, revision_id, visible_until_order, now,
    user_id, is_admin.
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
        raise RevisionNotFound("Resource not found.")
    revision = dict(record.data())

    action = RevisionAction(revision["action"])
    if action == RevisionAction.CREATED:
        raise RevisionCannotRevertCreate("Cannot revert a Creation revision.")

    resource_id: str = revision["resource_id"]
    resource_type: str = revision["resource_type"]
    # SEC-GR-014: validate labels before interpolation
    if resource_type not in _REVERT_LABEL_ALLOWLIST:
        raise RevisionInvalidAction("Cannot revert revision with an unknown resource type.")
    # Deserialize the before-snapshot exactly once; target_type lives in it
    # for UserNote — validate if present (SEC-GR-014).
    before_snapshot: dict[str, Any] = RevisionRepository._from_json(revision.get("before")) or {}
    target_type = before_snapshot.get("target_type")
    if target_type is not None and target_type not in _REVERT_LABEL_ALLOWLIST:
        raise RevisionInvalidAction("Cannot revert revision with an unknown target type.")
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
            raise RevisionNotFound("Resource not found.")
        resource_props: dict[str, Any] = dict(rec.data()["props"])

        if resource_props.get("origin") != "user":
            raise RevisionCannotRevertCanonical("Cannot revert a canonical or candidate resource.")

        # Owner check (PROB-02, #4) — fail closed: unowned/legacy resources
        # (stored_owner is None) require admin (SEC-AUTH-01).
        stored_owner = resource_props.get("user_id")
        if stored_owner != command["user_id"] and not command["is_admin"]:
            raise RevisionForbidden("This resource belongs to another user.")

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
            raise RevisionForbidden("This resource belongs to another user.")
        # Check if resource was already re-created (idempotency guard)
        result = await tx.run(
            "MATCH (r {id: $rid, series_id: $sid}) RETURN properties(r) AS props",
            rid=resource_id,
            sid=command["series_id"],
        )
        existing = await result.single()
        if existing is not None:
            raise RevisionAlreadyExists("This resource has already been re-created.")

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
        raise RevisionInvalidAction(f"Cannot revert revision with action: {action.value}")

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
