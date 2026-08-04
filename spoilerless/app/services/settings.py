"""Settings service — effective LLM config resolution (stored > env)."""

from __future__ import annotations

from typing import Any

from spoilerless.app.core.config import get_settings
from spoilerless.app.domain.settings import (
    LLMSettingsResponse,
    LLMSettingsUpdate,
    mask_api_key,
    settings_payload,
)
from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.repository.settings import SettingsRepository


class SettingsService:
    """Resolves and persists the LLM provider configuration.

    Precedence for every effective field: stored graph value first, then the
    ``LLM_*`` env/settings fallback. ``base_url`` for ``gemini`` falls back to
    the official Google endpoint when neither source provides one.
    """

    def __init__(self, database: Neo4jDatabase) -> None:
        self._repository = SettingsRepository(database)

    async def get_llm(self) -> LLMSettingsResponse:
        stored = await self._repository.get_llm() or {}
        settings = get_settings()
        provider = stored.get("provider") or settings.llm_provider
        api_key = stored.get("api_key") or settings.llm_api_key
        base_url = stored.get("base_url") or settings.llm_base_url
        model = stored.get("model") or settings.llm_model
        enabled = stored.get("enabled", settings.llm_enabled)
        return LLMSettingsResponse(
            provider=provider,
            model=model or None,
            base_url=base_url or None,
            enabled=bool(enabled),
            system_prompt_language=(
                stored.get("system_prompt_language", "english")
                or "english"
            ),
            api_key_configured=bool(api_key),
            api_key_masked=mask_api_key(api_key),
        )

    async def update_llm(self, update: LLMSettingsUpdate) -> LLMSettingsResponse:
        stored = await self._repository.get_llm() or {}
        merged: dict[str, Any] = dict(stored)
        merged["provider"] = update.provider
        if update.api_key:
            merged["api_key"] = update.api_key
        if update.base_url is not None:
            if update.base_url.strip():
                merged["base_url"] = update.base_url.strip()
            else:
                merged.pop("base_url", None)
        if update.model is not None:
            if update.model.strip():
                merged["model"] = update.model.strip()
            else:
                merged.pop("model", None)
        if update.enabled is not None:
            merged["enabled"] = update.enabled
        merged["system_prompt_language"] = update.system_prompt_language
        await self._repository.set_llm(
            settings_payload(
                provider=merged.get("provider", update.provider),
                api_key=merged.get("api_key"),
                base_url=merged.get("base_url"),
                model=merged.get("model"),
                enabled=merged.get("enabled"),
                system_prompt_language=merged.get(
                    "system_prompt_language", "english"
                ),
            )
        )
        return await self.get_llm()
