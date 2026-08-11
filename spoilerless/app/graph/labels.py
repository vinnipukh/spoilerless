"""Server-owned label inventories — single source of truth (PROB-09/#81).

Previously the story-label inventory was duplicated across seed.py and
setup.py (byte-identical copies) while retrieval/tools.py derived its own
set from the ontology's narrative group. ``NODE_LABELS`` is the full label
inventory the seed creates; ``STORY_LABELS`` is the visibility-audited
subset. The ontology-derived narrative-node set in retrieval/tools.py is a
different source (the ontology YAML) and deliberately stays there.
"""

NODE_LABELS = (
    "Series",
    "Episode",
    "Character",
    "Event",
    "Location",
    "Organization",
    "Object",
    "Claim",
    "Source",
    "EvidenceFragment",
    "UserNote",
    "Revision",
)

STORY_LABELS = ("Character", "Event", "Location", "Organization", "Object", "Claim", "EvidenceFragment", "Source")
