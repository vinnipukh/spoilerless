"""Localized, configurable insufficient-evidence fallback (conversational-tone policy).

Replaces the old robotic fallback ("The watched graph does not contain enough
information to answer that.") with warm, friendly, language-matched text per
the product brief: the fallback must follow the user's language, must not
mention "the graph", and must remain a guess rather than a confirmed fact.

The reply language follows the selected prompt language (the Settings
"Assistant language" choice) — the fallback text is overridable via
``LLM_FALLBACK_EN`` / ``LLM_FALLBACK_TR`` (see core/config.py). The old
Turkish-character language-detection helper was deleted: it is dead code
superseded by that prompt-language rule (PROB-28/#52).
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
