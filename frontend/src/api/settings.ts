import { apiFetch } from './client'
import type { LLMSettings, LLMSettingsUpdate } from '../types/settings'

export function getLLMSettings(): Promise<LLMSettings> {
  return apiFetch('/api/settings/llm')
}

export function updateLLMSettings(body: LLMSettingsUpdate): Promise<LLMSettings> {
  return apiFetch('/api/settings/llm', {
    method: 'PUT',
    body,
  })
}
