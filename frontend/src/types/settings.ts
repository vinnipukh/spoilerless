// Mirrors backend/app/domain/settings.py's LLMSettingsResponse / LLMSettingsUpdate
// field-for-field. The API key is write-only: the server never returns the full
// key — only `api_key_configured` + a masked `api_key_masked` suffix (T-06-07).

export type LLMProvider = 'gemini' | 'openai_compatible'

export type LLMSettings = {
  provider: LLMProvider
  model: string | null
  base_url: string | null
  api_key_configured: boolean
  api_key_masked: string | null
}

export type LLMSettingsUpdate = {
  provider: LLMProvider
  api_key?: string
  base_url?: string | null
  model?: string | null
}
