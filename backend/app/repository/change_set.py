"""Persistence for the ChangeSet Stage 1 (Propose) and Stage 2 (Confirm/Apply)
resource (RAG-11, RAG-12, RAG-14, RAG-15).

Every query is user-scoped through the authenticated ``(:AppUser)`` node —
a foreign or missing ``chat_session_id``/``change_set_id`` is indistinguishable
from a missing one (generic not-found), the same convention
``repository/chat.py`` uses.

Stage 2's ``_apply_change_set`` is the single highest-consequence write path
in the phase: it re-reads the ChangeSet, the current progress, and every
operation's target fresh **inside one Neo4j write transaction**
(``Neo4jDatabase.execute_write``), validates every operation in list order
before applying any of them, applies all of them plus exactly one
``RevisionRepository.log_revision`` call inside that same callback, and
relies on Neo4j's automatic rollback-on-exception semantics for full
rollback on any single operation's failure (06-PATTERNS.md Pattern 4).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import TypeAdapter

from backend.app.domain.change_set import ChangeSetOperation, ChangeSetResponse
from backend.app.domain.revision import RevisionAction
from backend.app.graph.change_set import (
    CHANGE_SET_ATTACH_EVIDENCE_QUERY,
    CHANGE_SET_CREATE_CLAIM_QUERY,
    CHANGE_SET_CREATE_NODE_QUERIES,
    CHANGE_SET_CREATE_NOTE_QUERIES,
    CHANGE_SET_CREATE_QUERY,
    CHANGE_SET_CREATE_RELATIONSHIP_QUERY,
    CHANGE_SET_DELETE_CLAIM_QUERY,
    CHANGE_SET_DELETE_NODE_QUERY,
    CHANGE_SET_DELETE_RELATIONSHIP_QUERY,
    CHANGE_SET_READ_FOR_APPLY_QUERY,
    CHANGE_SET_REVERT_DELETE_QUERY,
    CHANGE_SET_REVISION_GET_QUERY,
    CHANGE_SET_UPDATE_CLAIM_QUERY,
    CHANGE_SET_UPDATE_NODE_QUERY,
    CHANGE_SET_UPDATE_RELATIONSHIP_QUERY,
    CURRENT_PROGRESS_QUERY,
    MARK_CHANGE_SET_APPLIED_QUERY,
    MARK_CHANGE_SET_FAILED_QUERY,
    MARK_CHANGE_SET_REJECTED_QUERY,
    MARK_CHANGE_SET_REVERTED_QUERY,
    TARGET_VISIBILITY_QUERY,
)
from backend.app.graph.database import Neo4jDatabase
from backend.app.repository.user_content import NOTE_DELETE_QUERY, NOTE_UPDATE_QUERY
from backend.app.revisions import RevisionRepository

_OPERATION_ADAPTER: TypeAdapter[ChangeSetOperation] = TypeAdapter(ChangeSetOperation)


class ChangeSetSessionNotFound(LookupError):
    """The chat session is missing, or belongs to another user (indistinguishable)."""


class ChangeSetNotFound(LookupError):
    """No such ChangeSet for this user/series (indistinguishable from missing/cross-user)."""


class ChangeSetConflict(RuntimeError):
    """The ChangeSet is not in a state that can be confirmed/rejected again."""


class ChangeSetStale(RuntimeError):
    """The ChangeSet's snapshot boundary exceeds the current (since-lowered) progress."""


class ChangeSetOperationInvalid(ValueError):
    """An operation failed fresh re-validation at apply time — aborts the whole apply."""


class ChangeSetNotRevertible(RuntimeError):
    """The ChangeSet has no applied Revision to revert (never applied, rejected,
    failed, or already reverted) — "nothing to revert" (RAG-15)."""


class ChangeSetRevertUnsupported(ValueError):
    """The ChangeSet includes an update/delete-shaped operation with no stored
    prior state to restore — only create-shaped ChangeSets support revert
    (mirrors ``api/revisions.py::revert_revision``'s "cannot revert a
    Creation revision" discipline: some shapes have no well-defined restore
    target and are rejected rather than silently mishandled, RAG-15)."""


class ChangeSetRevertConflict(RuntimeError):
    """A resource this ChangeSet created was modified or removed by a later,
    unrelated change since this ChangeSet was applied — revert is aborted
    rather than silently overwriting that later change."""


# Only these operation types have a well-defined "pre-apply state" to
# restore without any stored per-operation snapshot: for a create, the
# pre-apply state is simply "the resource did not exist" — so revert is
# "delete what was created". Update/delete-shaped operations have no
# equivalent, since Stage 2 logs exactly one coarse ChangeSet-level Revision
# (RAG-12's "one Revision per apply", not one per operation/target) with no
# per-target `before` snapshot — restoring those would require inventing
# state that was never recorded.
_CREATE_OPERATION_TYPES = frozenset(
    {"create_node", "create_relationship", "create_claim", "attach_evidence", "create_note"}
)


@dataclass(frozen=True)
class _StaleResult:
    """Internal marker: the ``failed``-status write committed; caller must raise.

    ``_apply_change_set`` returns this (a *normal* return) instead of raising
    ``ChangeSetStale`` directly — raising inside the ``execute_write``
    callback would abort the whole managed transaction and roll back the
    very "mark as failed" write this case depends on. ``ChangeSetRepository
    .confirm`` inspects the return value after the transaction has committed
    and raises ``ChangeSetStale`` from there instead.
    """

    response: ChangeSetResponse


@dataclass(frozen=True)
class ProposeChangeSetCommand:
    id: str
    user_id: str
    series_id: str
    chat_session_id: str
    summary: str
    operations: list[Any]
    visible_until_order_snapshot: int
    created_at: datetime


@dataclass(frozen=True)
class ApplyChangeSetCommand:
    change_set_id: str
    user_id: str
    series_id: str
    now: datetime


@dataclass(frozen=True)
class RejectChangeSetCommand:
    change_set_id: str
    user_id: str
    series_id: str
    now: datetime


@dataclass(frozen=True)
class RevertChangeSetCommand:
    change_set_id: str
    user_id: str
    series_id: str
    now: datetime


def _normalize(record: dict[str, Any]) -> dict[str, Any]:
    """Convert Neo4j temporal types to Pydantic-compatible values."""
    result: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, bytes):
            result[key] = value
        elif hasattr(value, "iso_format"):
            result[key] = value.iso_format()
        elif hasattr(value, "to_native"):
            native = value.to_native()
            result[key] = native.isoformat() if hasattr(native, "isoformat") else str(native)
        else:
            result[key] = value
    return result


def _to_response(record: dict[str, Any]) -> ChangeSetResponse:
    normalized = _normalize(record)
    operations_json = normalized.pop("operations_json")
    normalized["operations"] = json.loads(operations_json)
    return ChangeSetResponse.model_validate(normalized)


class ChangeSetRepository:
    """Read/write access to the ChangeSet draft resource."""

    def __init__(self, database: Neo4jDatabase) -> None:
        self._database = database

    async def get_visible_target(
        self, target_id: str, series_id: str, visible_until_order: int
    ) -> dict[str, Any] | None:
        """Return the target's ``{id, origin, node_labels}`` if visible, else ``None``.

        Hidden, cross-series, and genuinely nonexistent targets are all
        indistinguishable — every case yields ``None`` (RAG-03).
        """
        records = await self._database.execute_query(
            TARGET_VISIBILITY_QUERY,
            target_id=target_id,
            series_id=series_id,
            visible_until_order=visible_until_order,
        )
        return records[0] if records else None

    async def propose(self, command: ProposeChangeSetCommand) -> ChangeSetResponse:
        """Persist the draft ChangeSet, or raise ``ChangeSetSessionNotFound``.

        Writes ONLY the ``ChangeSet`` node itself plus its linking
        relationships — no target node/relationship/claim is ever touched
        here (Stage 1 propose has zero graph-target mutation, RAG-11).
        """
        records = await self._database.execute_query(
            CHANGE_SET_CREATE_QUERY,
            id=command.id,
            user_id=command.user_id,
            series_id=command.series_id,
            chat_session_id=command.chat_session_id,
            summary=command.summary,
            operations_json=json.dumps(
                [op.model_dump(mode="json") for op in command.operations]
            ),
            visible_until_order_snapshot=command.visible_until_order_snapshot,
            created_at=command.created_at,
        )
        if not records:
            raise ChangeSetSessionNotFound(
                f"Chat session {command.chat_session_id} not found for this user."
            )
        return _to_response(records[0])

    async def confirm(self, command: ApplyChangeSetCommand) -> ChangeSetResponse:
        """Confirm and apply a ChangeSet inside one Neo4j write transaction.

        Raises ``ChangeSetNotFound`` (missing/cross-user, indistinguishable),
        ``ChangeSetConflict`` (already rejected/failed/reverted),
        ``ChangeSetStale`` (snapshot boundary exceeds current progress — the
        ChangeSet is marked ``failed`` and must be regenerated, never
        silently applied), or ``ChangeSetOperationInvalid`` (an operation
        failed fresh re-validation at apply time — the whole apply rolls
        back, zero partial writes). Confirming an already-``applied``
        ChangeSet a second time is a safe no-op: the original stored result
        is returned, with no second mutation and no second Revision
        (idempotency-key replay protection, RAG-12).

        The stale-marker write must *commit* (so the ChangeSet is durably
        ``failed`` and cannot be silently retried) — raising ``ChangeSetStale``
        from *inside* ``_apply_change_set`` would abort the whole managed
        transaction and roll back that very status write. So
        ``_apply_change_set`` returns a ``_StaleResult`` marker instead (a
        normal return, letting the transaction commit) and this wrapper
        raises ``ChangeSetStale`` afterward, once the commit is durable.
        """
        result = await self._database.execute_write(self._apply_change_set, command)
        if isinstance(result, _StaleResult):
            raise ChangeSetStale(
                f"ChangeSet {command.change_set_id} was proposed at a higher progress "
                "boundary than the current (since-lowered) progress; it must be "
                "regenerated, not applied."
            )
        return result

    async def reject(self, command: RejectChangeSetCommand) -> ChangeSetResponse:
        """Reject a ChangeSet with zero graph mutation.

        Raises ``ChangeSetNotFound`` (missing/cross-user) or
        ``ChangeSetConflict`` (already resolved — cannot reject/confirm
        twice).
        """
        return await self._database.execute_write(self._reject_change_set, command)

    async def revert(self, command: RevertChangeSetCommand) -> ChangeSetResponse:
        """Revert a previously applied ChangeSet, inside one write transaction.

        Follows ``api/revisions.py::revert_revision``'s read-branch-apply-log
        shape, adapted to Stage 2's coarser one-Revision-per-apply model
        (06-06): read the ChangeSet and its apply-time Revision fresh inside
        the transaction, branch on whether every operation is create-shaped
        (raising ``ChangeSetRevertUnsupported`` — the same "no prior state to
        restore" rejection Phase 4 applies to a plain Creation revision — if
        not), delete every resource this ChangeSet created only if it has not
        been touched since (a fresh ``updated_at`` comparison, guarding
        against silently overwriting a later, unrelated change), then log a
        new ``Reverted``-action Revision and mark the ChangeSet ``reverted``
        — all inside the same ``execute_write`` callback, never a second
        transaction.

        Raises ``ChangeSetNotFound`` (missing/cross-user, indistinguishable),
        ``ChangeSetNotRevertible`` (no applied Revision to revert — never
        applied, rejected, failed, or already reverted),
        ``ChangeSetRevertUnsupported`` (an update/delete-shaped operation has
        no stored prior state to restore), or ``ChangeSetRevertConflict`` (a
        created resource was modified or removed by a later, unrelated
        change — the whole revert rolls back, zero partial mutation).
        """
        return await self._database.execute_write(self._revert_change_set, command)

    @staticmethod
    async def _revert_change_set(tx: Any, command: RevertChangeSetCommand) -> ChangeSetResponse:
        row = await _read_change_set_row(
            tx, command.user_id, command.series_id, command.change_set_id
        )
        if row is None:
            raise ChangeSetNotFound(
                f"ChangeSet {command.change_set_id} not found for this user."
            )
        if row["status"] != "applied":
            raise ChangeSetNotRevertible(
                f"ChangeSet {command.change_set_id} has no applied Revision to revert "
                f"(status={row['status']!r})."
            )

        revision_id = row["revision_id"]
        assert revision_id, "an applied ChangeSet always has a revision_id"
        revision_record = await (
            await tx.run(
                CHANGE_SET_REVISION_GET_QUERY,
                revision_id=revision_id,
                series_id=command.series_id,
            )
        ).single()
        if revision_record is None:
            raise ChangeSetNotRevertible(
                f"Revision {revision_id} for ChangeSet {command.change_set_id} not found."
            )
        revision = _normalize(revision_record.data())
        after = RevisionRepository._from_json(revision.get("after")) or {}
        operation_types: list[str] = list(after.get("operation_types") or [])
        affected_ids: list[str] = list(after.get("affected_ids") or [])

        if any(op_type not in _CREATE_OPERATION_TYPES for op_type in operation_types):
            raise ChangeSetRevertUnsupported(
                f"ChangeSet {command.change_set_id} includes an update/delete operation "
                "with no stored prior state to restore; only create-shaped ChangeSets "
                "support revert."
            )

        for resource_id in affected_ids:
            deleted = await (
                await tx.run(
                    CHANGE_SET_REVERT_DELETE_QUERY,
                    change_set_id=command.change_set_id,
                    resource_id=resource_id,
                    series_id=command.series_id,
                )
            ).single()
            if deleted is None:
                raise ChangeSetRevertConflict(
                    f"Resource {resource_id} was modified or removed by a later, "
                    "unrelated change since this ChangeSet was applied; revert was "
                    "aborted to avoid overwriting that change."
                )

        current_progress = await _read_current_progress(
            tx, command.user_id, command.series_id
        )
        revert_visible_from_order = (
            current_progress
            if current_progress is not None
            else row["visible_until_order_snapshot"]
        )

        # Log the Reverted revision BEFORE marking the ChangeSet reverted —
        # never edits or deletes the original apply-time Revision node
        # (Task 1 acceptance criteria); this is a second, independent
        # Revision row, appended after it in creation order.
        revert_revision = await RevisionRepository.log_revision(
            tx,
            series_id=command.series_id,
            resource_type="ChangeSet",
            resource_id=command.change_set_id,
            action=RevisionAction.REVERTED,
            before={"operation_types": operation_types, "affected_ids": affected_ids},
            after=None,
            visible_from_order=revert_visible_from_order,
            created_at=command.now,
        )

        reverted_record = await (
            await tx.run(
                MARK_CHANGE_SET_REVERTED_QUERY,
                id=command.change_set_id,
                series_id=command.series_id,
                user_id=command.user_id,
                revert_revision_id=revert_revision["id"],
            )
        ).single()
        assert reverted_record is not None, "ChangeSet existence already confirmed above"
        return _to_response(_normalize(reverted_record.data()))

    @staticmethod
    async def _apply_change_set(
        tx: Any, command: ApplyChangeSetCommand
    ) -> ChangeSetResponse | _StaleResult:
        row = await _read_change_set_row(
            tx, command.user_id, command.series_id, command.change_set_id
        )
        if row is None:
            raise ChangeSetNotFound(
                f"ChangeSet {command.change_set_id} not found for this user."
            )

        if row["status"] == "applied":
            # Idempotency-key replay: the exact same result, zero new
            # mutation, zero new Revision (RAG-12).
            return _to_response(row)
        if row["status"] != "awaiting_confirmation":
            raise ChangeSetConflict(
                f"ChangeSet {command.change_set_id} is already {row['status']!r} "
                "and cannot be confirmed again."
            )

        current_progress = await _read_current_progress(
            tx, command.user_id, command.series_id
        )
        if current_progress is None or row["visible_until_order_snapshot"] > current_progress:
            # Never silently apply against a stale snapshot (RAG-14) — mark
            # this ChangeSet terminal (`failed`) so it cannot be retried
            # without regenerating a fresh proposal. This write MUST commit,
            # so we return normally (a _StaleResult marker) rather than
            # raising here — raising would abort this very transaction and
            # roll back the status write it depends on. `confirm()` raises
            # `ChangeSetStale` once this has actually committed.
            failed_record = await (
                await tx.run(
                    MARK_CHANGE_SET_FAILED_QUERY,
                    id=command.change_set_id,
                    series_id=command.series_id,
                    now=command.now,
                )
            ).single()
            assert failed_record is not None, "ChangeSet existence already confirmed above"
            return _StaleResult(_to_response(_normalize(failed_record.data())))

        operations = [
            _OPERATION_ADAPTER.validate_python(item)
            for item in json.loads(row["operations_json"])
        ]

        applied_ids: list[str] = []
        operation_types: list[str] = []
        for operation in operations:
            result = await _apply_one_operation(
                tx,
                operation,
                series_id=command.series_id,
                user_id=command.user_id,
                current_progress=current_progress,
                now=command.now,
            )
            applied_ids.append(result["id"])
            operation_types.append(operation.operation_type)

        # Exactly one Revision per apply, inside this same callback — never
        # a second, separate transaction (Task 1 acceptance criteria).
        revision = await RevisionRepository.log_revision(
            tx,
            series_id=command.series_id,
            resource_type="ChangeSet",
            resource_id=command.change_set_id,
            action=RevisionAction.CREATED,
            before=None,
            after={"operation_types": operation_types, "affected_ids": applied_ids},
            visible_from_order=current_progress,
            created_at=command.now,
        )

        idempotency_key = f"change-set-apply:{uuid4()}"
        applied_record = await (
            await tx.run(
                MARK_CHANGE_SET_APPLIED_QUERY,
                id=command.change_set_id,
                series_id=command.series_id,
                now=command.now,
                revision_id=revision["id"],
                idempotency_key=idempotency_key,
            )
        ).single()
        assert applied_record is not None, "ChangeSet existence already confirmed above"
        return _to_response(_normalize(applied_record.data()))

    @staticmethod
    async def _reject_change_set(tx: Any, command: RejectChangeSetCommand) -> ChangeSetResponse:
        record = await (
            await tx.run(
                MARK_CHANGE_SET_REJECTED_QUERY,
                id=command.change_set_id,
                series_id=command.series_id,
                user_id=command.user_id,
                now=command.now,
            )
        ).single()
        if record is not None:
            return _to_response(_normalize(record.data()))

        existing = await _read_change_set_row(
            tx, command.user_id, command.series_id, command.change_set_id
        )
        if existing is None:
            raise ChangeSetNotFound(
                f"ChangeSet {command.change_set_id} not found for this user."
            )
        raise ChangeSetConflict(
            f"ChangeSet {command.change_set_id} is already {existing['status']!r} "
            "and cannot be rejected again."
        )


async def _read_change_set_row(
    tx: Any, user_id: str, series_id: str, change_set_id: str
) -> dict[str, Any] | None:
    record = await (
        await tx.run(
            CHANGE_SET_READ_FOR_APPLY_QUERY,
            user_id=user_id,
            series_id=series_id,
            change_set_id=change_set_id,
        )
    ).single()
    return _normalize(record.data()) if record is not None else None


async def _read_current_progress(tx: Any, user_id: str, series_id: str) -> int | None:
    """Read the CURRENT EFFECTIVE boundary (D-13, D-05).

    ``effective = min(view_as_of_order, watched_through_order)`` — a
    ChangeSet proposed at a later boundary must never apply while the user
    views an earlier episode (EDIT-02 fail-closed).  The persisted
    ``visible_until_order`` echo tracks ``watched_through_order``, so it
    cannot be used here: with view=1/watched=3 it would report 3 and let a
    snapshot-3 ChangeSet apply at view 1.
    """
    record = await (
        await tx.run(CURRENT_PROGRESS_QUERY, user_id=user_id, series_id=series_id)
    ).single()
    if record is None:
        return None
    data = record.data()
    return min(data["view_as_of_order"], data["watched_through_order"])


async def _require_visible(
    tx: Any,
    target_id: str,
    series_id: str,
    visible_until_order: int,
    *,
    require_user_origin: bool = False,
) -> dict[str, Any]:
    """Fresh re-validation of a single target at apply time (RAG-14).

    Never trusts the propose-time snapshot — reuses the exact same
    label-agnostic ``TARGET_VISIBILITY_QUERY`` the propose stage validates
    against, evaluated against the freshly re-read current progress.
    """
    record = await (
        await tx.run(
            TARGET_VISIBILITY_QUERY,
            target_id=target_id,
            series_id=series_id,
            visible_until_order=visible_until_order,
        )
    ).single()
    if record is None:
        raise ChangeSetOperationInvalid(
            f"Target {target_id} is not a currently visible resource in this series."
        )
    row = _normalize(record.data())
    if require_user_origin and row.get("origin") != "user":
        raise ChangeSetOperationInvalid(
            f"Target {target_id} is not a user-owned resource and cannot be mutated directly."
        )
    return row


async def _run_apply(tx: Any, query: str, error_msg: str, **params: Any) -> dict[str, Any]:
    """Run one apply-stage write, raising ``ChangeSetOperationInvalid`` on no match.

    Any raised exception here propagates out of the ``execute_write``
    callback, giving Neo4j's automatic rollback-on-exception semantics —
    zero partial writes for the whole ChangeSet (Task 1 acceptance criteria).
    """
    record = await (await tx.run(query, **params)).single()
    if record is None:
        raise ChangeSetOperationInvalid(error_msg)
    return _normalize(record.data())


async def _apply_one_operation(
    tx: Any,
    operation: ChangeSetOperation,
    *,
    series_id: str,
    user_id: str,
    current_progress: int,
    now: datetime,
) -> dict[str, Any]:
    """Dispatch one operation to its apply-stage Cypher (RAG-12).

    ``visible_from_order`` is always ``current_progress`` — a server-computed
    parameter re-read fresh inside this same transaction — never a value
    derived from the operation payload (satisfies "derived visible_from_order
    exactly equal to current progress is accepted" by construction: there is
    no code path that could ever bind a higher value).
    """
    match operation.operation_type:
        case "create_node":
            await _require_visible(tx, operation.episode_id, series_id, current_progress)
            query = CHANGE_SET_CREATE_NODE_QUERIES.get(operation.node_type)
            if query is None:
                raise ChangeSetOperationInvalid(f"Unsupported node type: {operation.node_type}")
            return await _run_apply(
                tx,
                query,
                "create_node: episode target is not currently visible.",
                id=f"user-node:{uuid4()}",
                series_id=series_id,
                label=operation.label,
                episode_id=operation.episode_id,
                description=(operation.properties or {}).get("description"),
                visible_from_order=current_progress,
                user_id=user_id,
                now=now,
            )
        case "update_node":
            await _require_visible(
                tx, operation.node_id, series_id, current_progress, require_user_origin=True
            )
            return await _run_apply(
                tx,
                CHANGE_SET_UPDATE_NODE_QUERY,
                "update_node: target not found or not user-owned.",
                node_id=operation.node_id,
                series_id=series_id,
                label=operation.label,
                description=(operation.properties or {}).get("description"),
                now=now,
            )
        case "delete_node":
            await _require_visible(
                tx, operation.node_id, series_id, current_progress, require_user_origin=True
            )
            return await _run_apply(
                tx,
                CHANGE_SET_DELETE_NODE_QUERY,
                "delete_node: target not found or not user-owned.",
                node_id=operation.node_id,
                series_id=series_id,
            )
        case "create_relationship":
            await _require_visible(tx, operation.source_id, series_id, current_progress)
            await _require_visible(tx, operation.target_id, series_id, current_progress)
            await _require_visible(tx, operation.episode_id, series_id, current_progress)
            return await _run_apply(
                tx,
                CHANGE_SET_CREATE_RELATIONSHIP_QUERY,
                "create_relationship: an endpoint or episode is not currently visible.",
                id=f"user-rel:{uuid4()}",
                series_id=series_id,
                source_id=operation.source_id,
                target_id=operation.target_id,
                relationship_type=operation.relationship_type.value,
                episode_id=operation.episode_id,
                description=(operation.properties or {}).get("description"),
                visible_from_order=current_progress,
                user_id=user_id,
                now=now,
            )
        case "update_relationship":
            await _require_visible(
                tx,
                operation.relationship_id,
                series_id,
                current_progress,
                require_user_origin=True,
            )
            relationship_type = (
                operation.relationship_type.value if operation.relationship_type else None
            )
            return await _run_apply(
                tx,
                CHANGE_SET_UPDATE_RELATIONSHIP_QUERY,
                "update_relationship: target not found or not user-owned.",
                relationship_id=operation.relationship_id,
                series_id=series_id,
                relationship_type=relationship_type,
                description=(operation.properties or {}).get("description"),
                now=now,
            )
        case "delete_relationship":
            await _require_visible(
                tx,
                operation.relationship_id,
                series_id,
                current_progress,
                require_user_origin=True,
            )
            return await _run_apply(
                tx,
                CHANGE_SET_DELETE_RELATIONSHIP_QUERY,
                "delete_relationship: target not found or not user-owned.",
                relationship_id=operation.relationship_id,
                series_id=series_id,
            )
        case "create_claim":
            await _require_visible(tx, operation.subject_id, series_id, current_progress)
            await _require_visible(tx, operation.object_id, series_id, current_progress)
            await _require_visible(tx, operation.episode_id, series_id, current_progress)
            return await _run_apply(
                tx,
                CHANGE_SET_CREATE_CLAIM_QUERY,
                "create_claim: subject, object, or episode is not currently visible.",
                id=f"user-claim:{uuid4()}",
                series_id=series_id,
                subject_id=operation.subject_id,
                object_id=operation.object_id,
                predicate=operation.predicate.value,
                claim_type=operation.claim_type.value,
                confidence_level=operation.confidence_level.value,
                episode_id=operation.episode_id,
                description=(operation.properties or {}).get("description"),
                visible_from_order=current_progress,
                user_id=user_id,
                now=now,
            )
        case "update_claim":
            await _require_visible(
                tx, operation.claim_id, series_id, current_progress, require_user_origin=True
            )
            predicate = operation.predicate.value if operation.predicate else None
            confidence_level = (
                operation.confidence_level.value if operation.confidence_level else None
            )
            return await _run_apply(
                tx,
                CHANGE_SET_UPDATE_CLAIM_QUERY,
                "update_claim: target not found or not user-owned.",
                claim_id=operation.claim_id,
                series_id=series_id,
                predicate=predicate,
                confidence_level=confidence_level,
                description=(operation.properties or {}).get("description"),
                now=now,
            )
        case "delete_claim":
            await _require_visible(
                tx, operation.claim_id, series_id, current_progress, require_user_origin=True
            )
            return await _run_apply(
                tx,
                CHANGE_SET_DELETE_CLAIM_QUERY,
                "delete_claim: target not found or not user-owned.",
                claim_id=operation.claim_id,
                series_id=series_id,
            )
        case "attach_evidence":
            await _require_visible(tx, operation.claim_id, series_id, current_progress)
            await _require_visible(tx, operation.source_id, series_id, current_progress)
            await _require_visible(tx, operation.episode_id, series_id, current_progress)
            content_hash = hashlib.sha256(operation.text.encode("utf-8")).hexdigest()
            return await _run_apply(
                tx,
                CHANGE_SET_ATTACH_EVIDENCE_QUERY,
                "attach_evidence: claim, source, or episode is not currently visible.",
                id=f"user-evidence:{uuid4()}",
                series_id=series_id,
                claim_id=operation.claim_id,
                source_id=operation.source_id,
                episode_id=operation.episode_id,
                locator=operation.locator,
                text=operation.text,
                content_hash=content_hash,
                visible_from_order=current_progress,
                user_id=user_id,
                now=now,
            )
        case "create_note":
            await _require_visible(tx, operation.target_id, series_id, current_progress)
            query = CHANGE_SET_CREATE_NOTE_QUERIES.get(operation.target_type)
            if query is None:
                raise ChangeSetOperationInvalid(
                    f"Unsupported note target type: {operation.target_type}"
                )
            return await _run_apply(
                tx,
                query,
                "create_note: target is not currently visible.",
                id=f"user-note:{uuid4()}",
                series_id=series_id,
                target_type=operation.target_type.value,
                target_id=operation.target_id,
                content=operation.content,
                visible_from_order=current_progress,
                user_id=user_id,
                now=now,
            )
        case "update_note":
            await _require_visible(
                tx, operation.note_id, series_id, current_progress, require_user_origin=True
            )
            return await _run_apply(
                tx,
                NOTE_UPDATE_QUERY,
                "update_note: target not found.",
                id=operation.note_id,
                series_id=series_id,
                content=operation.content,
                updated_at=now,
            )
        case "delete_note":
            await _require_visible(
                tx, operation.note_id, series_id, current_progress, require_user_origin=True
            )
            return await _run_apply(
                tx,
                NOTE_DELETE_QUERY,
                "delete_note: target not found.",
                id=operation.note_id,
                series_id=series_id,
            )
        case _:  # pragma: no cover — the discriminated union is closed.
            raise ChangeSetOperationInvalid(
                f"Unsupported operation type: {operation.operation_type}"
            )
