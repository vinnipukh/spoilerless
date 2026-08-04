"""Settings API routes — LLM provider configuration (auth required).

The API key is write-only: GET returns a masked form, PUT accepts a new key
(blank keeps the stored one), and the full key never appears in any response
model or log (T-06-07).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from spoilerless.app.api.deps import DatabaseDependency, RequireAdminDependency
from spoilerless.app.core.errors import error_responses
from spoilerless.app.domain.settings import LLMSettingsResponse, LLMSettingsUpdate
from spoilerless.app.services.settings import SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"])


def get_settings_service(database: DatabaseDependency) -> SettingsService:
    return SettingsService(database)


SettingsServiceDependency = Annotated[SettingsService, Depends(get_settings_service)]


@router.get(
    "/llm",
    response_model=LLMSettingsResponse,
    summary="Get the effective LLM provider configuration (key masked)",
    responses={401: error_responses(401)[401]},
)
async def get_llm_settings(
    _admin: RequireAdminDependency,
    service: SettingsServiceDependency,
) -> LLMSettingsResponse:
    return await service.get_llm()


@router.put(
    "/llm",
    response_model=LLMSettingsResponse,
    summary="Update the LLM provider configuration",
    responses={401: error_responses(401)[401]},
)
async def update_llm_settings(
    update: LLMSettingsUpdate,
    _admin: RequireAdminDependency,
    service: SettingsServiceDependency,
) -> LLMSettingsResponse:
    return await service.update_llm(update)
