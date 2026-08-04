"""Localized, configurable insufficient-evidence fallback (conversational-tone policy).

Replaces the old robotic fallback ("The watched graph does not contain enough
information to answer that.") with warm, friendly, language-matched text per
the product brief: the fallback must follow the user's language, must not
mention "the graph", and must remain a guess rather than a confirmed fact.

Language detection is a simple Turkish-character heuristic — the seed corpus
and chat traffic are EN/TR, and the Turkish alphabet's distinctive characters
(ç ğ ı ö ş ü) are unambiguous. The fallback text is overridable via
``LLM_FALLBACK_EN`` / ``LLM_FALLBACK_TR`` (see core/config.py).
"""

from __future__ import annotations

INSUFFICIENT_EVIDENCE_FALLBACK_EN = (
    "The episodes you've watched do not give a firm answer yet. Still, based "
    "on what we have seen so far, I would not expect everything to remain "
    "simple. I can make a spoiler-free interpretation from the current "
    "events, but it would be a guess rather than a confirmed fact."
)

INSUFFICIENT_EVIDENCE_FALLBACK_TR = (
    "İzlediğin bölümler henüz bu konuda kesin bir cevap vermiyor. Yine de şu "
    "ana kadarki olaylara bakınca her şeyin sorunsuz ilerlemesini beklemezdim. "
    "Elimizdeki işaretlerden spoilersız bir yorum yapabilirim ama bunun kesin "
    "bilgi değil, bir tahmin olduğunu akılda tutmak gerekir."
)

DEFAULT_FALLBACKS: dict[str, str] = {
    "en": INSUFFICIENT_EVIDENCE_FALLBACK_EN,
    "tr": INSUFFICIENT_EVIDENCE_FALLBACK_TR,
}

_TURKISH_CHARS = "çğıöşüÇĞİÖŞÜ"


def detect_language(text: str) -> str:
    """Return ``'tr'`` when *text* contains Turkish-specific characters, else ``'en'``."""
    return "tr" if any(char in _TURKISH_CHARS for char in text) else "en"
