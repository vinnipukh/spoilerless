"""Watch-progress service — resolves the spoiler boundary server-side (RAG-01).

``resolve`` raises ``ProgressNotFoundError`` when no persisted record exists;
callers must fail closed (empty/fail-closed GraphRAG results) rather than
silently defaulting to a nonzero boundary.  Since the D-05 split (07-02),
``resolve`` returns the policy-computed ``effective_view_order`` (min of
``view_as_of_order`` and ``watched_through_order``), so every boundary consumer
(chat, retrieval pipeline, change sets) is fail-closed by construction.

``upsert`` enforces the D-06 rules server-side: the confirmed order must be a
persisted episode order of the series (never a client-invented order),
cross-series targets are rejected, ``view_as_of_order`` never exceeds
``watched_through_order``, and a view-only change never lowers watched
progress (PROG-01).
"""

from __future__ import annotations

from spoilerless.app.domain.progress import UserSeriesProgressResponse
from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.repository.progress import ProgressRepository
from spoilerless.app.services.series import SeriesService
from spoilerless.app.spoiler.policy import (
    InvalidVisibilityOrder,
    assert_visibility_invariants,
)


class ProgressNotFoundError(LookupError):
    """No persisted watch-progress record exists for (user, series).

    Callers must fail closed — never leak whether the series exists or
    silently default to a boundary.
    """


class ProgressSeriesNotFoundError(ProgressNotFoundError):
    """The series in the URL path is not a persisted series.

    Subclass of :class:`ProgressNotFoundError` so the API layer maps it to the
    identical generic not-found envelope (cross-series targets must be
    indistinguishable from any other missing resource).
    """


class ProgressService:
    """Thin orchestration over :class:`ProgressRepository`."""

    def __init__(self, database: Neo4jDatabase) -> None:
        self._repository = ProgressRepository(database)
        self._series = SeriesService(database)

    async def get(
        self, user_id: str, series_id: str
    ) -> UserSeriesProgressResponse | None:
        # Cheap WHERE-guarded backfill so pre-split records are readable
        # without a manual DB reset (D-07).
        await self._repository.ensure_migrated()
        return await self._repository.get(user_id, series_id)

    async def upsert(
        self,
        user_id: str,
        series_id: str,
        *,
        watched_through_order: int | None = None,
        view_as_of_order: int | None = None,
        visible_until_order: int | None = None,
    ) -> UserSeriesProgressResponse:
        """Confirm or view-only-update progress; returns the persisted row.

        ``visible_until_order`` is the legacy alias (PROG-04, D-21): when
        ``watched_through_order`` is absent it means the same confirmation.
        When neither boundary field is present the request is a view-only
        change (PROG-01): ``watched_through_order`` stays at its persisted
        value and only ``view_as_of_order`` moves.
        """
        await self._repository.ensure_migrated()

        if watched_through_order is None and visible_until_order is not None:
            watched_through_order = visible_until_order
        watched_provided = watched_through_order is not None

        # D-06: the target must be a persisted series — cross-series updates
        # are rejected (indistinguishable generic not-found).
        series = await self._series.get_series(series_id)
        if series is None:
            raise ProgressSeriesNotFoundError(f"No series {series_id}.")

        # D-09: visibility/progress orders resolve against the persisted
        # episode orders, never client-invented orders.
        episodes = await self._series.list_episodes(series_id)
        persisted_orders = {episode["episode_order"] for episode in episodes}

        existing = await self._repository.get(user_id, series_id)

        if watched_provided:
            if watched_through_order not in persisted_orders:
                raise InvalidVisibilityOrder(
                    f"Order {watched_through_order} is not a persisted episode "
                    f"order of series {series_id}."
                )
            watched = watched_through_order
            view = (
                watched_through_order
                if view_as_of_order is None
                else view_as_of_order
            )
        else:
            # View-only change: requires an existing record and never lowers
            # the persisted watched boundary (PROG-01).
            if existing is None:
                raise ProgressNotFoundError(
                    f"No watch progress for user {user_id} on series {series_id}."
                )
            if view_as_of_order is None:
                raise InvalidVisibilityOrder(
                    "A view-only change requires view_as_of_order."
                )
            watched = existing.watched_through_order
            view = view_as_of_order

        if view not in persisted_orders:
            raise InvalidVisibilityOrder(
                f"Order {view} is not a persisted episode order of series "
                f"{series_id}."
            )
        # D-05 invariant (1 <= view <= watched) — enforced by the policy
        # service (assert_visibility_invariants raises on violation).
        assert_visibility_invariants(
            {"view_as_of_order": view, "watched_through_order": watched}
        )

        return await self._repository.upsert(
            user_id, series_id, watched_through_order=watched, view_as_of_order=view
        )

    async def resolve(self, user_id: str, series_id: str) -> int:
        """Resolve the effective boundary; raises ``ProgressNotFoundError``.

        Returns ``effective_view_order`` (min of the persisted split fields,
        computed by the policy service) so every boundary consumer is
        fail-closed against a request above the selected view (D-05, D-12).
        """
        record = await self.get(user_id, series_id)
        if record is None:
            raise ProgressNotFoundError(
                f"No watch progress for user {user_id} on series {series_id}."
            )
        return record.effective_view_order
