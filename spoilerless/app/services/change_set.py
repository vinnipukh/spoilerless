"""ChangeSet service — Stage 1 (Propose) and Stage 2 (Confirm/Apply)
orchestration (RAG-11, RAG-12, RAG-13, RAG-14, RAG-15).

Validates every operation's target server-side (existence, series scope,
current visibility) in list order BEFORE any persistence happens — an
invalid operation anywhere in the list means nothing is written at all
(no partial draft). Direct-mutation operations targeting an
``origin:canonical``/``origin:candidate`` resource are never persisted as
requested; the service transparently substitutes an honest
``create_note``-shaped override proposal referencing that resource instead
(06-PRD-SOURCE.md §10 — "do not claim the assistant can overwrite canonical
history when it cannot").

``confirm``/``reject`` are thin orchestration over
``ChangeSetRepository.confirm``/``reject`` — every actual re-validation
(fresh progress read, fresh per-operation target visibility, transactional
apply + single Revision log) happens repository-side, inside one Neo4j write
transaction, per 06-PATTERNS.md Pattern 4. This service layer never itself
calls ``tx.run`` — it only translates repository sentinel exceptions for the
API layer, exactly like ``propose`` already does for
``ChangeSetSessionNotFound``/``ChangeSetValidationError``.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from spoilerless.app.domain.change_set import (
    DIRECT_MUTATION_OPERATION_TYPES,
    ChangeSetCreateRequest,
    ChangeSetOperation,
    ChangeSetResponse,
    CreateNoteOperation,
)
from spoilerless.app.domain.user_content import NoteTargetType
from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.repository.change_set import (
    ApplyChangeSetCommand,
    ChangeSetConflict,
    ChangeSetNotFound,
    ChangeSetNotRevertible,
    ChangeSetOperationInvalid,
    ChangeSetRepository,
    ChangeSetRevertConflict,
    ChangeSetRevertUnsupported,
    ChangeSetSessionNotFound,
    ChangeSetStale,
    ProposeChangeSetCommand,
    RejectChangeSetCommand,
    RevertChangeSetCommand,
)
from spoilerless.app.services.progress import ProgressService

__all__ = [
    "ChangeSetService",
    "ChangeSetConflict",
    "ChangeSetNotFound",
    "ChangeSetNotRevertible",
    "ChangeSetOperationInvalid",
    "ChangeSetRevertConflict",
    "ChangeSetRevertUnsupported",
    "ChangeSetSessionNotFound",
    "ChangeSetStale",
    "ChangeSetValidationError",
]


class ChangeSetValidationError(ValueError):
    """An operation's target failed server-side validation before persistence."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# Which fields on each operation type name a target resource that must exist,
# belong to the series, and be currently visible before the ChangeSet can be
# persisted (06-PRD-SOURCE.md §9 — "ensure targets belong to the selected
# series" / "ensure targets are currently visible").
def _operation_target_ids(op: ChangeSetOperation) -> list[str]:
    match op.operation_type:
        case "create_node":
            return [op.episode_id]
        case "update_node" | "delete_node":
            return [op.node_id]
        case "create_relationship":
            return [op.source_id, op.target_id, op.episode_id]
        case "update_relationship" | "delete_relationship":
            return [op.relationship_id]
        case "create_claim":
            return [op.subject_id, op.object_id, op.episode_id]
        case "update_claim" | "delete_claim":
            return [op.claim_id]
        case "attach_evidence":
            return [op.claim_id, op.source_id, op.episode_id]
        case "create_note":
            return [op.target_id]
        case "update_note" | "delete_note":
            return [op.note_id]
        case _:  # pragma: no cover — the discriminated union is closed.
            raise ChangeSetValidationError(f"Unsupported operation type: {op.operation_type}")


# The single primary target id whose ``origin`` the canonical/candidate
# protection invariant checks for a direct-mutation operation.
def _primary_target_id(op: ChangeSetOperation) -> str:
    match op.operation_type:
        case "update_node" | "delete_node":
            return op.node_id
        case "update_relationship" | "delete_relationship":
            return op.relationship_id
        case "update_claim" | "delete_claim":
            return op.claim_id
        case _:  # pragma: no cover — only called for DIRECT_MUTATION_OPERATION_TYPES.
            raise ChangeSetValidationError(
                f"Unsupported direct-mutation operation type: {op.operation_type}"
            )


def _note_target_type(node_labels: list[str]) -> NoteTargetType:
    if "Claim" in node_labels:
        return NoteTargetType.CLAIM
    if "Character" in node_labels:
        return NoteTargetType.CHARACTER
    raise ChangeSetValidationError(
        "Canonical/candidate protection cannot construct an override note for this "
        "resource type — the existing Note mechanism only links to Character or Claim."
    )


def _override_note_content(target_id: str, origin: str) -> str:
    """Honest override-proposal copy — never claims the canonical/candidate
    resource itself was altered (06-PRD-SOURCE.md §10/§11)."""
    return (
        f"{target_id} is {origin}-origin content and stays exactly as it is — it "
        "cannot be edited or removed directly. This note proposes a linked "
        f"annotation instead; the {origin} record itself remains untouched."
    )


class ChangeSetService:
    """Orchestrates ChangeSet Stage-1 propose validation and persistence."""

    def __init__(
        self,
        database: Neo4jDatabase,
        progress_service: ProgressService | None = None,
    ) -> None:
        self._database = database
        self._repository = ChangeSetRepository(database)
        self._progress = progress_service or ProgressService(database)

    async def propose(
        self,
        user_id: str,
        series_id: str,
        request: ChangeSetCreateRequest,
        *,
        visible_until_order: int | None = None,
    ) -> ChangeSetResponse:
        """Validate every operation in list order, then persist the draft.

        Raises ``ProgressNotFoundError`` (propagated from ``ProgressService``)
        when no persisted boundary exists, ``ChangeSetValidationError`` when
        any operation's target fails validation, and
        ``ChangeSetSessionNotFound`` for a foreign/missing chat session.
        Nothing is ever persisted unless every operation validates.

        ``visible_until_order`` short-circuits the progress re-resolve when
        the caller already holds the turn boundary (PROBLEMS #78): the
        retrieval pipeline resolves progress once per turn and threads it
        down, so a ``propose_changeset`` tool call no longer pays a second
        DB read and cannot drift from the context the model saw. Callers
        without a fresh boundary (the API route) omit it and re-resolve.
        """
        if visible_until_order is None:
            boundary = await self._progress.resolve(user_id, series_id)
        else:
            boundary = visible_until_order

        resolved_operations: list[ChangeSetOperation] = []
        for operation in request.operations:
            resolved_operations.append(
                await self._validate_and_protect(operation, series_id, boundary)
            )

        return await self._repository.propose(
            ProposeChangeSetCommand(
                id=f"change-set:{uuid4()}",
                user_id=user_id,
                series_id=series_id,
                chat_session_id=request.chat_session_id,
                summary=request.summary,
                operations=resolved_operations,
                visible_until_order_snapshot=boundary,
                created_at=_utc_now(),
            )
        )

    async def confirm(
        self, user_id: str, series_id: str, change_set_id: str
    ) -> ChangeSetResponse:
        """Confirm and apply a ChangeSet — Stage 2 (RAG-12, RAG-14).

        Delegates entirely to ``ChangeSetRepository.confirm``, which re-reads
        the ChangeSet, the current progress, and every operation's target
        fresh inside a single Neo4j write transaction. Raises
        ``ChangeSetNotFound``, ``ChangeSetConflict``, ``ChangeSetStale``, or
        ``ChangeSetOperationInvalid`` — see that method's docstring.
        """
        return await self._repository.confirm(
            ApplyChangeSetCommand(
                change_set_id=change_set_id,
                user_id=user_id,
                series_id=series_id,
                now=_utc_now(),
            )
        )

    async def reject(
        self, user_id: str, series_id: str, change_set_id: str
    ) -> ChangeSetResponse:
        """Reject a ChangeSet with zero graph mutation (RAG-14).

        Raises ``ChangeSetNotFound`` or ``ChangeSetConflict`` (already
        resolved — cannot reject/confirm twice).
        """
        return await self._repository.reject(
            RejectChangeSetCommand(
                change_set_id=change_set_id,
                user_id=user_id,
                series_id=series_id,
                now=_utc_now(),
            )
        )

    async def revert(
        self, user_id: str, series_id: str, change_set_id: str
    ) -> ChangeSetResponse:
        """Revert a previously applied ChangeSet (RAG-15).

        Delegates entirely to ``ChangeSetRepository.revert``. Raises
        ``ChangeSetNotFound``, ``ChangeSetNotRevertible`` (no applied
        Revision to revert), ``ChangeSetRevertUnsupported`` (an update/
        delete-shaped operation has no stored prior state to restore), or
        ``ChangeSetRevertConflict`` (a created resource was modified or
        removed by a later, unrelated change) — see that method's docstring.
        """
        return await self._repository.revert(
            RevertChangeSetCommand(
                change_set_id=change_set_id,
                user_id=user_id,
                series_id=series_id,
                now=_utc_now(),
            )
        )

    async def _validate_and_protect(
        self, operation: ChangeSetOperation, series_id: str, boundary: int
    ) -> ChangeSetOperation:
        # PROB-09/#77: the per-target visibility checks ran serially; run
        # them concurrently (they are independent single-row reads).
        target_ids = _operation_target_ids(operation)
        rows = await asyncio.gather(
            *(
                self._repository.get_visible_target(target_id, series_id, boundary)
                for target_id in target_ids
            )
        )
        resolved: dict[str, dict[str, object]] = {}
        for target_id, row in zip(target_ids, rows):
            if row is None:
                raise ChangeSetValidationError(
                    f"Target {target_id} is not a currently visible resource in this series."
                )
            resolved[target_id] = row

        if operation.operation_type not in DIRECT_MUTATION_OPERATION_TYPES:
            return operation

        primary_id = _primary_target_id(operation)
        origin = resolved[primary_id].get("origin")
        if origin not in ("canonical", "candidate"):
            return operation

        target_type = _note_target_type(list(resolved[primary_id].get("node_labels") or []))
        return CreateNoteOperation(
            operation_type="create_note",
            target_type=target_type,
            target_id=primary_id,
            content=_override_note_content(primary_id, str(origin)),
        )
