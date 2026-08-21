"""Constants and mapping dictionaries for visualization projections."""

from __future__ import annotations

from spoilerless.app.domain.visualization import (
    DISPLAY_TIER_CORE,
    DISPLAY_TIER_DETAIL,
    DISPLAY_TIER_SUPPORTING,
    EXPANSION_KEY_CONFLICT,
    EXPANSION_KEY_FAMILY,
    EXPANSION_KEY_LOCATIONS,
    EXPANSION_KEY_WORK,
)

# D-13: Episode Overview omits participation/occurrence/location edges; they
# surface as timeline metadata, avatars/chips, or Inspector detail instead.
OMITTED_EDGE_TYPES = frozenset(
    {
        "PARTICIPATED_IN",
        "OCCURRED_IN",
        "LOCATED_IN",
        "WITNESSED",
        "CAUSED",
        "AFFECTED",
        "TARGETED",
        "MENTIONED",
    }
)

# D-14: raw Neo4j relation names stay hidden outside explicit debug mode; the
# Episode Overview carries human semantic edge classes only.
HUMAN_EDGE_CLASSES: dict[str, str] = {
    "PART_OF": "part_of",
    "PRECEDES": "precedes",
    "KNOWS": "knows",
    "FAMILY_OF": "family",
    "WORKS_WITH": "work",
    "TRUSTS": "trusts",
    "DISTRUSTS": "distrusts",
    "HELPS": "helps",
    "OPPOSES": "opposes",
    "THREATENS": "threatens",
    "ATTACKS": "attacks",
    "KILLS": "kills",
}

# D-14: the ``full`` view (D-11 Advanced mode) maps the participation family
FULL_EDGE_CLASSES: dict[str, str] = {
    **HUMAN_EDGE_CLASSES,
    "PARTICIPATED_IN": "participated_in",
    "OCCURRED_IN": "occurred_in",
    "LOCATED_IN": "located_in",
    "WITNESSED": "witnessed",
    "CAUSED": "caused",
    "AFFECTED": "affected",
    "TARGETED": "targeted",
    "MENTIONED": "mentioned",
}

# D-10: Variant A keeps characters plus major Events; Episode/Series containers stay as structural context.
KEPT_NODE_KINDS = frozenset({"Series", "Episode", "Character"})
CONTAINER_KINDS = frozenset({"Series", "Episode"})

# D-12: major/supporting/micro event tiers map to D-15 display tiers.
EVENT_TIER_DISPLAY_TIER = {
    "major": DISPLAY_TIER_CORE,
    "supporting": DISPLAY_TIER_SUPPORTING,
    "micro": DISPLAY_TIER_DETAIL,
}

# D-15 claim-status tiers for the ``investigation`` view.
CLAIM_STATUS_DISPLAY_TIER = {
    "canonical": DISPLAY_TIER_CORE,
    "corroborated": DISPLAY_TIER_SUPPORTING,
    "candidate": DISPLAY_TIER_DETAIL,
}

SUPPORTED_BY_EDGE_CLASS = "supported_by"
FROM_SOURCE_EDGE_CLASS = "from_source"

# D-21: relation families per expansion key.
EXPANSION_EDGE_TYPES: dict[str, frozenset[str]] = {
    EXPANSION_KEY_FAMILY: frozenset({"FAMILY_OF"}),
    EXPANSION_KEY_WORK: frozenset({"WORKS_WITH"}),
    EXPANSION_KEY_CONFLICT: frozenset(
        {"OPPOSES", "THREATENS", "ATTACKS", "KILLS", "DISTRUSTS"}
    ),
    EXPANSION_KEY_LOCATIONS: frozenset({"LOCATED_IN", "OCCURRED_IN"}),
}

EXPANSION_NEIGHBOR_KEYS = (
    EXPANSION_KEY_FAMILY,
    EXPANSION_KEY_WORK,
    EXPANSION_KEY_CONFLICT,
)
