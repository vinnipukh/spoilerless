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
from functools import partial
from typing import Any
from uuid import uuid4

from pydantic import TypeAdapter

from spoilerless.app.domain.change_set import ChangeSetOperation, ChangeSetResponse
from spoilerless.app.domain.revision import RevisionAction
from spoilerless.app.graph.change_set import (
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
from spoilerless.app.graph.database import Neo4jDatabase, neo4j_row_to_python, run_single

# Single row-normalization definition (PROB-09/#68).
_normalize = neo4j_row_to_python
from spoilerless.app.repository.user_content import NOTE_DELETE_QUERY, NOTE_UPDATE_QUERY
from spoilerless.app.revisions.repository import RevisionRepository
from spoilerless.app.spoiler.visibility import derive_visible_from_order

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
            user_id=command.user_id,
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
            user_id=command.user_id,
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


# Shared run → single → raise → normalize helper (PROB-09/#68), bound to
# the ChangeSet exception type. Errors propagate out of the execute_write
# callback, giving Neo4j's automatic rollback-on-exception semantics — zero
# partial writes for the whole ChangeSet (Task 1 acceptance criteria).
_run_apply = partial(run_single, exc_type=ChangeSetOperationInvalid)


def _op_description(operation: ChangeSetOperation) -> Any:
    """The single description extraction — was repeated in five cases."""
    return (operation.properties or {}).get("description")


def _visible_from_episode(episode: dict[str, Any] | None, current_progress: int) -> int:
    """The single visibility-derivation rule for every create op.

    ``visible_from_order`` is always derived from the server-re-read episode
    (or, for notes, the current-progress floor) — never from the operation
    payload (RAG-12: there is no code path that could bind a higher value).
    """
    return derive_visible_from_order(
        episode.get("visible_from_order") if episode else None, current_progress
    )


@dataclass(frozen=True)
class _ApplySpec:
    """Apply-stage dispatch row (PROB-09/#67).

    ``targets`` are operation field names re-validated at apply time via
    ``_require_visible`` (RAG-14 fresh re-validation); ``requires_episode``
    additionally fetches the operation's episode row once as the derivation
    base; ``id_kind`` generates the ``user-{kind}:{uuid4()}`` id; ``params``
    builds the exact write params (the per-op parameter shapes genuinely
    differ, so they stay in small builders instead of forcing one giant
    signature).
    """

    query: str | Callable[[ChangeSetOperation], str | None]
    targets: tuple[str, ...] = ()
    require_user_origin: bool = False
    requires_episode: bool = False
    id_kind: str | None = None
    error_msg: str = "operation target is not currently visible."
    query_error: str = ""
    params: Callable[[ChangeSetOperation, dict[str, Any], dict[str, Any] | None], dict[str, Any]] | None = None


def _create_params(
    operation: ChangeSetOperation,
    ctx: dict[str, Any],
    episode: dict[str, Any] | None,
    *,
    with_description: bool = True,
    **extra: Any,
) -> dict[str, Any]:
    """Shared create-op params: generated id, derivation, description."""
    base: dict[str, Any] = {
        "id": ctx["id_value"],
        "series_id": ctx["series_id"],
        "user_id": ctx["user_id"],
        "now": ctx["now"],
        "visible_from_order": _visible_from_episode(episode, ctx["current_progress"]),
    }
    if with_description:
        base["description"] = _op_description(operation)
    base.update(extra)
    return base


def _params_create_node(op: ChangeSetOperation, ctx: dict[str, Any], episode: dict[str, Any] | None) -> dict[str, Any]:
    return _create_params(op, ctx, episode, label=op.label, episode_id=op.episode_id)


def _params_update_node(op: ChangeSetOperation, ctx: dict[str, Any], episode: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "node_id": op.node_id, "series_id": ctx["series_id"], "label": op.label,
        "description": _op_description(op), "now": ctx["now"],
    }


def _params_delete_node(op: ChangeSetOperation, ctx: dict[str, Any], episode: dict[str, Any] | None) -> dict[str, Any]:
    return {"node_id": op.node_id, "series_id": ctx["series_id"]}


def _params_create_relationship(op: ChangeSetOperation, ctx: dict[str, Any], episode: dict[str, Any] | None) -> dict[str, Any]:
    return _create_params(
        op, ctx, episode,
        source_id=op.source_id, target_id=op.target_id,
        relationship_type=op.relationship_type.value, episode_id=op.episode_id,
    )


def _params_update_relationship(op: ChangeSetOperation, ctx: dict[str, Any], episode: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "relationship_id": op.relationship_id, "series_id": ctx["series_id"],
        "relationship_type": op.relationship_type.value if op.relationship_type else None,
        "description": _op_description(op), "now": ctx["now"],
    }


def _params_delete_relationship(op: ChangeSetOperation, ctx: dict[str, Any], episode: dict[str, Any] | None) -> dict[str, Any]:
    return {"relationship_id": op.relationship_id, "series_id": ctx["series_id"]}


def _params_create_claim(op: ChangeSetOperation, ctx: dict[str, Any], episode: dict[str, Any] | None) -> dict[str, Any]:
    return _create_params(
        op, ctx, episode,
        subject_id=op.subject_id, object_id=op.object_id,
        predicate=op.predicate.value, claim_type=op.claim_type.value,
        confidence_level=op.confidence_level.value, episode_id=op.episode_id,
    )


def _params_update_claim(op: ChangeSetOperation, ctx: dict[str, Any], episode: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "claim_id": op.claim_id, "series_id": ctx["series_id"],
        "predicate": op.predicate.value if op.predicate else None,
        "confidence_level": op.confidence_level.value if op.confidence_level else None,
        "description": _op_description(op), "now": ctx["now"],
    }


def _params_delete_claim(op: ChangeSetOperation, ctx: dict[str, Any], episode: dict[str, Any] | None) -> dict[str, Any]:
    return {"claim_id": op.claim_id, "series_id": ctx["series_id"]}


def _params_attach_evidence(op: ChangeSetOperation, ctx: dict[str, Any], episode: dict[str, Any] | None) -> dict[str, Any]:
    return _create_params(
        op, ctx, episode, with_description=False,
        claim_id=op.claim_id, source_id=op.source_id, episode_id=op.episode_id,
        locator=op.locator, text=op.text,
        content_hash=hashlib.sha256(op.text.encode("utf-8")).hexdigest(),
    )


def _params_create_note(op: ChangeSetOperation, ctx: dict[str, Any], episode: dict[str, Any] | None) -> dict[str, Any]:
    # A note carries no episode signal — its visibility follows the current
    # progress floor through the same shared rule.
    return _create_params(
        op, ctx, None, with_description=False,
        target_type=op.target_type.value, target_id=op.target_id, content=op.content,
    )


def _params_update_note(op: ChangeSetOperation, ctx: dict[str, Any], episode: dict[str, Any] | None) -> dict[str, Any]:
    return {"id": op.note_id, "series_id": ctx["series_id"], "content": op.content, "updated_at": ctx["now"]}


def _params_delete_note(op: ChangeSetOperation, ctx: dict[str, Any], episode: dict[str, Any] | None) -> dict[str, Any]:
    return {"id": op.note_id, "series_id": ctx["series_id"]}


def _node_type_query(operation: ChangeSetOperation) -> str | None:
    return CHANGE_SET_CREATE_NODE_QUERIES.get(operation.node_type)


def _note_target_query(operation: ChangeSetOperation) -> str | None:
    return CHANGE_SET_CREATE_NOTE_QUERIES.get(operation.target_type)


# Table-driven apply dispatch (PROB-09/#67): one row per operation type —
# query (fixed or per-node-type map), apply-time re-validation targets,
# episode derivation base, generated id, error copy, and the param builder.
_APPLY_SPECS: dict[str, _ApplySpec] = {
    "create_node": _ApplySpec(
        _node_type_query, requires_episode=True, id_kind="node",
        error_msg="create_node: episode target is not currently visible.",
        query_error="Unsupported node type: {node_type}", params=_params_create_node,
    ),
    "update_node": _ApplySpec(
        CHANGE_SET_UPDATE_NODE_QUERY, targets=("node_id",), require_user_origin=True,
        error_msg="update_node: target not found or not user-owned.", params=_params_update_node,
    ),
    "delete_node": _ApplySpec(
        CHANGE_SET_DELETE_NODE_QUERY, targets=("node_id",), require_user_origin=True,
        error_msg="delete_node: target not found or not user-owned.", params=_params_delete_node,
    ),
    "create_relationship": _ApplySpec(
        CHANGE_SET_CREATE_RELATIONSHIP_QUERY, targets=("source_id", "target_id"),
        requires_episode=True, id_kind="rel",
        error_msg="create_relationship: an endpoint or episode is not currently visible.",
        params=_params_create_relationship,
    ),
    "update_relationship": _ApplySpec(
        CHANGE_SET_UPDATE_RELATIONSHIP_QUERY, targets=("relationship_id",), require_user_origin=True,
        error_msg="update_relationship: target not found or not user-owned.",
        params=_params_update_relationship,
    ),
    "delete_relationship": _ApplySpec(
        CHANGE_SET_DELETE_RELATIONSHIP_QUERY, targets=("relationship_id",), require_user_origin=True,
        error_msg="delete_relationship: target not found or not user-owned.",
        params=_params_delete_relationship,
    ),
    "create_claim": _ApplySpec(
        CHANGE_SET_CREATE_CLAIM_QUERY, targets=("subject_id", "object_id"),
        requires_episode=True, id_kind="claim",
        error_msg="create_claim: subject, object, or episode is not currently visible.",
        params=_params_create_claim,
    ),
    "update_claim": _ApplySpec(
        CHANGE_SET_UPDATE_CLAIM_QUERY, targets=("claim_id",), require_user_origin=True,
        error_msg="update_claim: target not found or not user-owned.", params=_params_update_claim,
    ),
    "delete_claim": _ApplySpec(
        CHANGE_SET_DELETE_CLAIM_QUERY, targets=("claim_id",), require_user_origin=True,
        error_msg="delete_claim: target not found or not user-owned.", params=_params_delete_claim,
    ),
    "attach_evidence": _ApplySpec(
        CHANGE_SET_ATTACH_EVIDENCE_QUERY, targets=("claim_id", "source_id"),
        requires_episode=True, id_kind="evidence",
        error_msg="attach_evidence: claim, source, or episode is not currently visible.",
        params=_params_attach_evidence,
    ),
    "create_note": _ApplySpec(
        _note_target_query, targets=("target_id",), id_kind="note",
        error_msg="create_note: target is not currently visible.",
        query_error="Unsupported note target type: {target_type}", params=_params_create_note,
    ),
    "update_note": _ApplySpec(
        NOTE_UPDATE_QUERY, targets=("note_id",), require_user_origin=True,
        error_msg="update_note: target not found.", params=_params_update_note,
    ),
    "delete_note": _ApplySpec(
        NOTE_DELETE_QUERY, targets=("note_id",), require_user_origin=True,
        error_msg="delete_note: target not found.", params=_params_delete_note,
    ),
}


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

    ``visible_from_order`` is always ``current_progress``-derived — a
    server-computed parameter re-read fresh inside this same transaction —
    never a value from the operation payload (satisfies \"derived
    visible_from_order exactly equal to current progress is accepted\" by
    construction).
    """
    spec = _APPLY_SPECS.get(operation.operation_type)
    if spec is None:  # pragma: no cover — the discriminated union is closed.
        raise ChangeSetOperationInvalid(
            f"Unsupported operation type: {operation.operation_type}"
        )

    # Apply-time fresh re-validation of every required target (RAG-14).
    for target_name in spec.targets:
        await _require_visible(
            tx,
            getattr(operation, target_name),
            series_id,
            current_progress,
            require_user_origin=spec.require_user_origin,
        )
    episode = None
    if spec.requires_episode:
        episode = await _require_visible(tx, operation.episode_id, series_id, current_progress)

    query = spec.query(operation) if callable(spec.query) else spec.query
    if query is None:
        raise ChangeSetOperationInvalid(
            spec.query_error.format(**operation.model_dump())
        )

    ctx = {
        "series_id": series_id,
        "user_id": user_id,
        "now": now,
        "current_progress": current_progress,
        "id_value": f"user-{spec.id_kind}:{uuid4()}" if spec.id_kind else None,
    }
    params = spec.params(operation, ctx, episode) if spec.params else {}
    return await _run_apply(tx, query, spec.error_msg, **params)
