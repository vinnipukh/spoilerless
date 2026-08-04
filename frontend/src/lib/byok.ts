// BYOK (bring-your-own-key) LLM settings, frontend half of D-06 (AI-01):
// the provider key/base_url/model live ONLY in this browser's localStorage
// under 'hdgraf:byok-llm-settings' and travel per-request as X-LLM-* headers.
// The key never leaves this browser except as a request header to the user's
// configured endpoint - nothing here touches the network, and no
// settings-persistence endpoint is involved (AI-01, D-05).
import type { StoredLLMSettings } from '@/types/settings'

export const BYOK_STORAGE_KEY = 'hdgraf:byok-llm-settings'

/**
 * Read the stored BYOK settings from localStorage. Absent or malformed
 * storage returns null and never throws - the settings form must stay
 * usable regardless of what is (or is not) in the browser.
 */
export function getStoredLLMSettings(): StoredLLMSettings | null {
  try {
    const raw = window.localStorage.getItem(BYOK_STORAGE_KEY)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    if (typeof parsed !== 'object' || parsed === null) return null
    const candidate = parsed as Partial<StoredLLMSettings>
    if (typeof candidate.provider !== 'string' || typeof candidate.api_key !== 'string') {
      return null
    }
    return {
      provider: candidate.provider as StoredLLMSettings['provider'],
      api_key: candidate.api_key,
      base_url: typeof candidate.base_url === 'string' ? candidate.base_url : '',
      model: typeof candidate.model === 'string' ? candidate.model : '',
    }
  } catch {
    return null
  }
}

/**
 * Persist the BYOK settings, trimming all three free-text fields on write
 * (matches the backend's whitespace-only-key rejection).
 */
export function saveLLMSettings(settings: StoredLLMSettings): void {
  const trimmed: StoredLLMSettings = {
    provider: settings.provider,
    api_key: settings.api_key.trim(),
    base_url: settings.base_url.trim(),
    model: settings.model.trim(),
  }
  window.localStorage.setItem(BYOK_STORAGE_KEY, JSON.stringify(trimmed))
}

/**
 * Headers for chat requests (D-06): X-LLM-Api-Key and X-LLM-Provider always
 * (together they're enough for Gemini - no base_url needed), plus
 * X-LLM-Base-URL / X-LLM-Model when non-blank. A missing or whitespace-only
 * key returns {} so the backend falls back to its own config and the key is
 * never sent anywhere.
 */
export function getLLMHeaders(): Record<string, string> {
  const settings = getStoredLLMSettings()
  if (!settings) return {}
  const apiKey = settings.api_key.trim()
  if (!apiKey) return {}
  const headers: Record<string, string> = {
    'X-LLM-Api-Key': apiKey,
    'X-LLM-Provider': settings.provider,
  }
  const baseUrl = settings.base_url.trim()
  const model = settings.model.trim()
  if (baseUrl) headers['X-LLM-Base-URL'] = baseUrl
  if (model) headers['X-LLM-Model'] = model
  return headers
}
