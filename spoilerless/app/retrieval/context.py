"""Context-section registry — the single source of truth for RAG context layout.

Shared by the retrieval pipeline (``assemble_context`` renders sections in
``CONTEXT_SECTIONS`` order) and the system prompt (``CONTEXT_DELIMITERS``
tags, referenced by name in the prompt prose). One definition, two
consumers — the "keep in sync" comments that used to span both files are
gone (PROB-09/#64). The section order is the documented fixed contract
(06-CONTEXT.md RAG-05): series context, boundary, entities, relationships,
claims, evidence, sources, notes, then chat_history as the trailing ninth.
"""

from __future__ import annotations

from typing import Any, Callable

CONTEXT_SECTIONS: tuple[str, ...] = (
    "series_context",
    "boundary",
    "entities",
    "relationships",
    "claims",
    "evidence",
    "sources",
    "notes",
    "chat_history",
)

# Exact delimiter tags the pipeline wraps context sections in; the system
# prompt references them by name and the prompt-injection tests assert the
# order. Derived from CONTEXT_SECTIONS so the two can never drift.
CONTEXT_DELIMITERS: tuple[str, ...] = tuple(f"<{name}>" for name in CONTEXT_SECTIONS)


def _neutralize(text: str | None) -> str:
    """Escape angle brackets so delimiter-shaped tags are inert text.

    D-12: user/retrieved content may contain literal `<claims>`-style tags;
    if passed through verbatim they could close/reopen the pipeline's section
    framing. Escaping both brackets makes them text, not syntax.
    """
    return (text or "").replace("<", "&lt;").replace(">", "&gt;")


def _entity_line(item: dict[str, Any]) -> str:
    return f"- {_neutralize(item.get('label') or item.get('id'))} ({item.get('id')}, {item.get('type')})"


def _edge_line(item: dict[str, Any]) -> str:
    return (
        f"- {item.get('source')} -[{_neutralize(item.get('type'))}]-> "
        f"{item.get('target')} ({item.get('id')})"
    )


def _claim_line(item: dict[str, Any]) -> str:
    return (
        f"- {_neutralize(item.get('label') or item.get('id'))} ({item.get('id')}): "
        f"{item.get('subject_id')} {_neutralize(item.get('predicate'))} {item.get('object_id')}"
    )


def _evidence_line(item: dict[str, Any]) -> str:
    return f"- {_neutralize(item.get('label') or item.get('id'))} ({item.get('id')}): {_neutralize(item.get('text') or '')}"


def _source_line(item: dict[str, Any]) -> str:
    return (
        f"- {_neutralize(item.get('label') or item.get('id'))} ({item.get('id')}, "
        f"{item.get('source_type')}): {_neutralize(item.get('locator') or '')}"
    )


def _note_line(item: dict[str, Any]) -> str:
    content = _neutralize(item.get("content") or "").strip()
    return f"- {content or item.get('id')}"


# Item-list section → line formatter, in CONTEXT_SECTIONS order. The three
# non-item sections (series_context / boundary / chat_history) have bespoke
# renderers inside assemble_context.
ITEM_SECTION_FORMATTERS: dict[str, Callable[[dict[str, Any]], str]] = {
    "entities": _entity_line,
    "relationships": _edge_line,
    "claims": _claim_line,
    "evidence": _evidence_line,
    "sources": _source_line,
    "notes": _note_line,
}
