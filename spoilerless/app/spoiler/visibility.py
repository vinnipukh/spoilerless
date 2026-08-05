"""Single shared visibility-derivation rule (PROB-25, #49).

Before this module there were two forked rules for deriving a user-created
resource's ``visible_from_order``: the direct user-content API stamped the
target episode's ``episode_order`` inside Cypher, while the ChangeSet apply
path stamped the freshly re-read ``current_progress`` and silently discarded
the operation's episode choice. #49 flagged that fork as a spoiler-safety
hazard — two code paths that can disagree about when a node becomes visible.

``derive_visible_from_order`` is now the ONE rule both create paths call:
the resource becomes visible at ``max(episode order, current progress)``,
fail-closed. Rationale:

- A node authored *about* episode N must never be visible before episode N
  (``episode_order`` floor).
- A node authored *while the user is at* progress P must never leak below P
  either (``current_progress`` floor) — the ChangeSet apply invariant.
- Absent both signals, fail closed to ``1`` (the earliest visible boundary),
  never ``0``/``None`` (a null ``visible_from_order`` fails the seed-integrity
  audit and would make the node permanently invisible or, worse, un-filtered).

Keeping this as a pure Python helper (no DB, no Cypher) means the rule is
unit-testable in isolation and impossible to fork again without deleting this
function — the grep gate in 09-03's verification asserts no inline
``visible_from_order``/``episode_order`` derivation survives outside here.
"""
from __future__ import annotations


def derive_visible_from_order(
    episode_order: int | None = None,
    current_progress: int | None = None,
) -> int:
    """Return the single derived ``visible_from_order`` for a user-created resource.

    The resource becomes visible at ``max(episode_order, current_progress)``,
    fail-closed: the result is never less than ``1`` and never ``None``. When
    both inputs are absent (or non-positive), the resource is visible from the
    earliest boundary (``1``) rather than being assigned an invalid/null order.

    Args:
        episode_order: The order of the episode the resource is authored about,
            or ``None`` when the create path has no episode signal (e.g. a note
            whose visibility follows its target, handled by the caller).
        current_progress: The user's current effective progress boundary at
            authoring time, or ``None`` on the direct API where no progress is
            in scope.

    Returns:
        A positive integer ``visible_from_order`` (``>= 1``).
    """
    candidates = [
        value
        for value in (episode_order, current_progress)
        if value is not None and value >= 1
    ]
    if not candidates:
        return 1
    return max(candidates)
